import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from report.calc_average import calculate_averages
from report.csv_utils import save_csv_with_data
from events.normalize import normalize, PROCESS_START_LABEL
from events.reader import RunFileError, parse_run, read_run

FIX = Path(__file__).parent / "fixtures"


def run_of(*lines, header='{"type":"run_start","schema":2,"run_id":"r1","platform":"android","app_init_ms":0}'):
    return parse_run("\n".join((header,) + lines) + "\n")


def ev(seq, t, msg, mode="SYNC", src="AD"):
    return (f'{{"type":"event","seq":{seq},"t_ms":{t},"src":"{src}","mode":"{mode}",'
            f'"level":"DEBUG","msg":"{msg}"}}')


def test_happy_path():
    run = read_run(FIX / "happy.jsonl", expected_run_id="20261124-083600-it01")
    assert run.header.device == "Pixel 8" and run.end.reason == "flush" and not run.truncated
    assert len(run.events) == 6
    out = normalize(run)
    msgs = [e["msg"] for e in out.entries]
    assert msgs[0] == PROCESS_START_LABEL
    assert msgs[1:] == ["MainApplication.onCreate -> Start", "Worker -> Queued", "MainActivity.onCreate -> Start",
                        "https://example.com/api", "[200] https://example.com/api", "App.tsx -> Render"]
    assert out.entries[0]["time"] == 180 and out.entries[0]["duration"] == 180
    assert out.entries[1]["type"] == "AD" and out.entries[-1]["type"] == "RN"


def test_sync_duration_rule_with_interleaved_async():
    out = normalize(run_of(ev(1, 100, "a"), ev(2, 150, "b", "ASYNC"), ev(3, 300, "c"), ev(4, 310, "d")))
    assert [(e["time"], e["duration"]) for e in out.entries] == [(100, 100), (150, 0), (300, 200), (310, 10)]


def test_duplicate_suffixes():
    out = normalize(run_of(ev(1, 1, "x"), ev(2, 2, "x"), ev(3, 3, "y"), ev(4, 4, "x")))
    assert [e["msg"] for e in out.entries] == ["x", "x(1)", "y", "x(2)"]


def test_req_rsp_pairing_and_unmatched_request():
    net = lambda seq, t, ph, rid, extra="": (
        f'{{"type":"net","seq":{seq},"t_ms":{t},"phase":"{ph}","req_id":{rid},"url":"u{rid}"{extra}}}')
    out = normalize(run_of(net(1, 100, "REQ", 1), net(2, 120, "REQ", 2), net(3, 400, "RSP", 2, ',"status":404,"dur_ms":1'),
                           net(4, 900, "RSP", 1, ',"status":200,"dur_ms":5')))
    rsp = {e["msg"]: e for e in out.entries if e["req_rsp"] == "RSP"}
    assert rsp["[404] u2"]["duration"] == 280 and rsp["[200] u1"]["duration"] == 800
    run = run_of(net(1, 100, "REQ", 7))
    out = normalize(run)
    assert out.entries[0]["req_rsp"] == "REQ" and out.entries[0]["duration"] == 0
    assert any("req_id 7" in w for w in out.warnings)


def test_truncated_last_line():
    run = read_run(FIX / "truncated.jsonl")
    assert run.truncated and len(run.events) == 1
    assert any("run_end is missing" in w for w in run.warnings)


def test_truncated_middle_line_is_error():
    with pytest.raises(RunFileError, match="invalid JSON"):
        parse_run('{"type":"run_start","schema":2,"run_id":"r","platform":"ios"}\n{bad\n' + ev(1, 1, "a") + "\n")


def test_wrong_schema_and_run_id_and_empty():
    with pytest.raises(RunFileError, match="unsupported schema"):
        read_run(FIX / "wrong_schema.jsonl")
    with pytest.raises(RunFileError, match="run_id mismatch"):
        read_run(FIX / "happy.jsonl", expected_run_id="other")
    with pytest.raises(RunFileError, match="empty"):
        parse_run("")
    with pytest.raises(RunFileError, match="cannot read"):
        read_run(FIX / "missing.jsonl")


def test_t0_modes():
    run = read_run(FIX / "happy.jsonl")
    ps = normalize(run, "process_start")
    ai = normalize(run, "app_init")
    assert ps.effective_t0 == "process_start" and ai.effective_t0 == "app_init"
    assert ai.entries[0]["msg"] == "MainApplication.onCreate -> Start"
    assert [e["time"] for e in ai.entries][:3] == [20, 70, 120]
    assert ai.entries[0]["duration"] == 20
    with pytest.raises(ValueError):
        normalize(run, "bogus")


def test_app_init_drops_events_before_init():
    out = normalize(run_of(ev(1, 50, "early"), ev(2, 150, "late"),
                           header='{"type":"run_start","schema":2,"run_id":"r","platform":"android","app_init_ms":100}'),
                    "app_init")
    assert [e["msg"] for e in out.entries] == ["late"]


def test_prewarmed_falls_back_to_app_init():
    run = read_run(FIX / "prewarmed.jsonl")
    out = normalize(run, "process_start")
    assert out.effective_t0 == "app_init" and [e["msg"] for e in out.entries] == ["A"]
    assert any("prewarm" in w for w in out.warnings)


def test_feeds_v1_averages_and_csv(tmp_path):
    entries = []
    for _ in range(2):
        entries.extend(normalize(read_run(FIX / "happy.jsonl")).entries)
    avgs = calculate_averages(entries)
    assert all(a["count"] == 2 for a in avgs)
    params = SimpleNamespace(csv_path=str(tmp_path / "a.csv"), csv_net_path=str(tmp_path / "n.csv"),
                             platform="android", package="com.flowdiagram", bundle_id="", wait_time=10,
                             launch_times=2, open_csv=False)
    save_csv_with_data(avgs, params)
    rows = list(csv.reader(open(params.csv_path)))
    assert rows[0][:4] == ["Time", "Duration", "Type", "Message"]
    assert any(r[2] == "NET - RSP" and r[1] == "293" for r in rows)
    assert len(list(csv.reader(open(params.csv_net_path)))) == 3


def test_feeds_v1_png(tmp_path):
    pytest.importorskip("matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    from report.visualize import save_png_with_data
    avgs = calculate_averages(normalize(read_run(FIX / "happy.jsonl")).entries)
    params = SimpleNamespace(png_path=str(tmp_path / "a.png"), open_png=False)
    save_png_with_data(avgs, params)
    assert Path(params.png_path).stat().st_size > 0
