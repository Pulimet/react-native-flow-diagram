from pathlib import Path

import pytest

from conftest import make_params
from platforms.base import Platform, PlatformError, RunFileNotFound
from platforms.completion import WaitSettings, has_run_end, wait_and_fetch
from run_loop import FatalRunError, load_from_dir, report_meta, start_measurements
from report.calc_average import calculate_averages

FIX = Path(__file__).parent / "fixtures"
HAPPY = (FIX / "happy.jsonl").read_text()
HAPPY_ID = "20261124-083600-it01"


class FakePlatform(Platform):
    name = "fake"

    def __init__(self, params, text=HAPPY, fail_on=()):
        super().__init__(params)
        self.text, self.fail_on, self.events, self.id = text, set(fail_on), [], None

    def validate(self): pass
    def prepare(self): pass

    def launch(self, run_id):
        self.events.append(("launch", run_id))
        self.id = run_id
        if len(self.events) // 3 + 1 in self.fail_on:
            raise PlatformError("device went away")
        return {"total_time_ms": 100 * len([e for e in self.events if e[0] == "launch"])}

    def fetch(self, run_id, dest):
        self.events.append(("fetch", run_id))
        Path(dest).write_text(self.text.replace(HAPPY_ID, run_id))
        return Path(dest)

    def stop(self): self.events.append(("stop", self.id))
    def discard(self, run_id): self.events.append(("discard", run_id))


def loop_params(tmp_path, **over):
    return make_params(raw_dir=str(tmp_path / "raw"), **over)


def no_sleep(_):
    pass


def test_run_loop_three_runs(tmp_path):
    params = loop_params(tmp_path)
    platform = FakePlatform(params)
    result = start_measurements(platform, params, sleep=no_sleep)
    assert len(result.runs) == 3 and not result.failures
    raw = sorted((tmp_path / "raw").glob("*.jsonl"))
    assert len(raw) == 3 and len({p.name for p in raw}) == 3
    # fetch happens before stop for every run, and each run has its own id
    kinds = [e[0] for e in platform.events]
    assert kinds[:4] == ["launch", "fetch", "stop", "discard"]
    averages = calculate_averages(result.entries)
    assert all(a["count"] == 3 for a in averages)
    assert report_meta(result, platform)["system_total_time_ms"] == 200


def test_run_loop_honors_t0_and_survives_a_failed_run(tmp_path):
    params = loop_params(tmp_path, t0="app_init")
    result = start_measurements(FakePlatform(params, fail_on={2}), params, sleep=no_sleep)
    assert len(result.runs) == 2 and len(result.failures) == 1 and "device went away" in result.failures[0]
    assert result.effective_t0 == "app_init"
    assert "Process start -> App init" not in {e["msg"] for e in result.entries}


def test_run_loop_bad_file_is_a_failure_and_debug_build_is_fatal(tmp_path):
    params = loop_params(tmp_path, launch_times=1)
    result = start_measurements(FakePlatform(params, text="not json\n"), params, sleep=no_sleep)
    assert not result.runs and len(result.failures) == 1
    debug = HAPPY.replace('"debuggable":false', '"debuggable":true')
    with pytest.raises(FatalRunError):
        start_measurements(FakePlatform(params, text=debug), params, sleep=no_sleep)
    allowed = loop_params(tmp_path, launch_times=1, allow_debuggable=True)
    assert len(start_measurements(FakePlatform(allowed, text=debug), allowed, sleep=no_sleep).runs) == 1


def test_load_from_dir(tmp_path):
    (tmp_path / "a.jsonl").write_text(HAPPY)
    (tmp_path / "b.jsonl").write_text((FIX / "truncated.jsonl").read_text())
    result = load_from_dir(tmp_path, make_params())
    assert len(result.runs) == 2
    with pytest.raises(PlatformError):
        load_from_dir(tmp_path / "missing", make_params())


# ---- completion detection
class Scripted(FakePlatform):
    """fetch returns the next scripted payload (None = file not there yet), repeating the last one."""

    def __init__(self, params, script):
        super().__init__(params)
        self.script, self.calls = list(script), 0

    def fetch(self, run_id, dest):
        item = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        if item is None:
            raise RunFileNotFound("not yet")
        Path(dest).write_text(item)
        return Path(dest)


class Clock:
    def __init__(self):
        self.now = 0.0

    def sleep(self, s):
        self.now += s

    def __call__(self):
        return self.now


def wait(platform, tmp_path, **settings):
    clock = Clock()
    s = WaitSettings(**{"settle": 1, "poll_interval": 1, "stable_polls": 2, "timeout": 10, **settings})
    path = wait_and_fetch(platform, "r", tmp_path / "r.jsonl", s, sleep=clock.sleep, clock=clock)
    return path, clock.now


START = '{"type":"run_start","schema":2,"run_id":"r","platform":"android"}\n'
END = '{"type":"run_end","seq":2,"t_ms":1,"reason":"flush"}\n'


def test_has_run_end():
    assert has_run_end((START + END).encode()) and not has_run_end(START.encode())
    assert not has_run_end((START + '{"type":"run_en').encode()) and not has_run_end(b"")


def test_wait_stops_at_run_end(tmp_path):
    p = Scripted(make_params(), [None, START, START + END])
    path, t = wait(p, tmp_path)
    assert path.read_text().endswith(END) and p.calls == 3 and t == 3


def test_wait_stops_when_file_is_stable(tmp_path):
    p = Scripted(make_params(), [START, START + "x\n", START + "x\n"])
    _, t = wait(p, tmp_path, stable_polls=1)
    assert p.calls == 3
    p = Scripted(make_params(), [START])
    wait(p, tmp_path, stable_polls=2)
    assert p.calls == 3  # first read + two identical repeats


def test_wait_timeout_returns_partial_or_errors(tmp_path):
    growing = [START + "x" * i for i in range(1, 50)]
    path, t = wait(Scripted(make_params(), growing), tmp_path, timeout=5)
    assert path.exists() and t == 5
    with pytest.raises(PlatformError, match="no run file"):
        wait(Scripted(make_params(), [None]), tmp_path, timeout=4)
