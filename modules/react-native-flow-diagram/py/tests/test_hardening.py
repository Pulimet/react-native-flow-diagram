import json
import subprocess

import pytest

from conftest import FakeRunner, make_params
from events.reader import RunFileError, parse_run, read_run
from platforms import base
from platforms.android import AndroidPlatform
from platforms.base import PlatformError, RunFileNotFound
from platforms.completion import WaitSettings, wait_and_fetch

HEADER = ('{"type":"run_start","schema":2,"run_id":"r1","platform":"android","app_id":"a","app_version":"1",'
          '"build":"release","debuggable":false,"os":"15","device":"x","t0":"process_start","app_init_ms":50.0,'
          '"prewarmed":false}')
EVENT = '{"type":"event","seq":1,"t_ms":1.0,"src":"AD","mode":"SYNC","level":"DEBUG","msg":"m","thread":"main"}'


# ---- reader: killed mid-write, stale files, odd content
def test_truncated_mid_utf8_character_is_tolerated(tmp_path):
    f = tmp_path / "r1.jsonl"
    f.write_bytes((HEADER + "\n" + EVENT + "\n").encode() + '{"type":"event","seq":2,"msg":"é'.encode()[:-1])
    run = read_run(f, expected_run_id="r1")
    assert run.truncated and len(run.events) == 1


def test_file_cut_inside_header_is_a_clear_error():
    with pytest.raises(RunFileError, match="invalid JSON"):
        parse_run(HEADER[:40])


def test_stale_file_from_earlier_run_is_rejected(tmp_path):
    f = tmp_path / "new.jsonl"
    f.write_text(HEADER + "\n" + EVENT + "\n")
    with pytest.raises(RunFileError, match="run_id mismatch"):
        read_run(f, expected_run_id="r2")


def test_message_with_escapes_and_unicode_roundtrips():
    msg = 'q"\\\n\t\u0001\u2028 \U0001F600 ' + "x" * 5000
    line = json.dumps({"type": "event", "seq": 1, "t_ms": 1.0, "src": "AD", "mode": "SYNC", "msg": msg})
    assert "\n" not in line
    assert parse_run(HEADER + "\n" + line + "\n").events[0].msg == msg


# ---- completion: timeouts
class StubPlatform:
    def __init__(self, data):
        self.data = data
        self.fetches = 0

    def fetch(self, run_id, dest):
        self.fetches += 1
        if self.data is None:
            raise RunFileNotFound("nope")
        dest.write_bytes(self.data)
        return dest


def fake_clock():
    t = [0.0]

    def clock():
        return t[0]

    def sleep(s):
        t[0] += max(s, 0.5)
    return clock, sleep


def test_timeout_without_file_explains_causes(tmp_path):
    clock, sleep = fake_clock()
    with pytest.raises(PlatformError, match="no run file after 5s"):
        wait_and_fetch(StubPlatform(None), "r1", tmp_path / "r1.jsonl", WaitSettings(0, 1, 2, 5), sleep, clock)


def test_growing_file_returns_partial_after_timeout(tmp_path, capsys):
    clock, sleep = fake_clock()
    p = StubPlatform(b"x")
    orig = p.fetch

    def growing(run_id, dest):
        p.data = p.data + b"x"
        return orig(run_id, dest)
    p.fetch = growing
    assert wait_and_fetch(p, "r1", tmp_path / "r1.jsonl", WaitSettings(0, 1, 2, 5), sleep, clock)
    assert "partial" in capsys.readouterr().out


# ---- host tool failures
def test_run_command_timeout_and_missing_tool(monkeypatch):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired("adb", 1)
    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(PlatformError, match="timed out"):
        base.run_command(["adb", "devices"], timeout=1)

    def missing(*a, **k):
        raise FileNotFoundError("adb")
    monkeypatch.setattr(subprocess, "run", missing)
    with pytest.raises(PlatformError, match="not found on PATH"):
        base.run_command(["adb", "devices"])


def android(runner, **over):
    p = AndroidPlatform(make_params(**over), runner)
    p.serial = "S1"
    return p


def test_wrong_activity_is_reported():
    runner = FakeRunner().when("am start", "Error type 3\nError: Activity class does not exist.\n")
    with pytest.raises(PlatformError, match="am start failed"):
        android(runner).launch("r1")


def test_locked_secure_device_is_an_error(monkeypatch):
    monkeypatch.setattr("platforms.android.time.sleep", lambda s: None)
    runner = FakeRunner().when("dumpsys window", "isKeyguardShowing=true")
    with pytest.raises(PlatformError, match="locked"):
        android(runner).ensure_unlocked()


def test_swipe_locked_device_is_dismissed(monkeypatch):
    monkeypatch.setattr("platforms.android.time.sleep", lambda s: None)
    answers = iter(["isKeyguardShowing=true", "isKeyguardShowing=false"])

    runner = FakeRunner()
    original = runner.__call__

    def call(cmd, timeout=None):
        if "dumpsys" in cmd:
            res = original(cmd, timeout)
            res.stdout = next(answers)
            return res
        return original(cmd, timeout)
    android(call).ensure_unlocked()
