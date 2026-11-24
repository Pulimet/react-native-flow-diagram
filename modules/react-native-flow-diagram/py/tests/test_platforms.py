import json
from pathlib import Path

import pytest

from conftest import FakeRunner, make_params
from platforms import create_platform
from platforms.android import AndroidPlatform
from platforms.base import PlatformError, RunFileNotFound
from platforms.ios_device import IosDevicePlatform
from platforms.ios_simulator import IosSimulatorPlatform

PKG = "com.flowdiagram"
ADB_ONE = "List of devices attached\nRFCXB13QAVF\tdevice\n\n"


def android(runner, **over):
    return AndroidPlatform(make_params(**over), runner)


def ready_android(**over):
    runner = FakeRunner().when("adb devices", ADB_ONE).when("pm list packages", f"package:{PKG}\n")
    p = android(runner, **over)
    p.validate()
    return p, runner


# ---- Android
def test_android_validate_picks_single_device_and_labels_emulator():
    runner = FakeRunner().when("adb devices", "List of devices attached\nemulator-5554\tdevice\n\n") \
        .when("pm list packages", f"package:{PKG}\n")
    p = android(runner)
    p.validate()
    assert p.serial == "emulator-5554" and p.emulated and "functional" in p.note()
    assert "adb -s emulator-5554 shell pm list packages com.flowdiagram" in runner.lines()


def test_android_validate_errors():
    two = "List of devices attached\nA\tdevice\nB\tdevice\n\n"
    with pytest.raises(PlatformError, match="--serial"):
        android(FakeRunner().when("adb devices", two)).validate()
    with pytest.raises(PlatformError, match="unauthorized"):
        android(FakeRunner().when("adb devices", "List of devices attached\nA\tunauthorized\n"), serial="A").validate()
    with pytest.raises(PlatformError, match="not installed"):
        android(FakeRunner().when("adb devices", ADB_ONE).when("pm list packages", "package:other\n")).validate()


def test_android_rejects_debuggable_unless_allowed():
    def make(**over):
        r = FakeRunner().when("adb devices", ADB_ONE).when("pm list packages", f"package:{PKG}\n") \
            .when("dumpsys package", "pkgFlags=[ DEBUGGABLE HAS_CODE ]")
        return android(r, **over)

    with pytest.raises(PlatformError, match="debuggable"):
        make().validate()
    make(allow_debuggable=True).validate()


def test_android_prepare_compile_and_clear():
    p, runner = ready_android(compile_mode="speed-profile")
    runner.when("settings get", "300000\n").when("cmd package compile", "Success\n")
    p.prepare()
    lines = runner.lines()
    assert f"adb -s RFCXB13QAVF shell cmd package compile -m speed-profile -f {PKG}" in lines
    assert any(l.startswith("adb -s RFCXB13QAVF shell rm -f /sdcard/Android/data/com.flowdiagram/files/flowdiagram/runs/*.jsonl")
               for l in lines)
    assert lines[-1].endswith(f"am force-stop {PKG}")
    p.cleanup()
    assert "settings put system screen_off_timeout 300000" in runner.lines()[-2]


def test_android_compile_mode_none_skips_compile():
    p, runner = ready_android(compile_mode="none")
    p.prepare()
    assert not any("compile" in l for l in runner.lines())


def test_android_launch_command_and_metrics():
    p, runner = ready_android()
    runner.when("am start", "Starting: Intent\nStatus: ok\nTotalTime: 812\nWaitTime: 830\nComplete\n")
    assert p.launch("rid-1") == {"total_time_ms": 812, "wait_time_ms": 830}
    assert runner.lines()[-1] == (
        "adb -s RFCXB13QAVF shell am start -W -S -n com.flowdiagram/com.flowdiagram.MainActivity "
        "--ez FlowDiagramFlag true --es FlowDiagramRunId rid-1")


def test_android_launch_downloads_sink_and_error():
    p, runner = ready_android(sink="downloads")
    p.launch("rid-1")
    assert runner.lines()[-1].endswith("--es FlowDiagramSink downloads")
    runner.when("am start", "Error: Activity class does not exist.", returncode=0)
    with pytest.raises(PlatformError, match="am start failed"):
        p.launch("rid-2")


def test_android_fetch_primary_then_downloads_fallback(tmp_path):
    p, runner = ready_android()
    dest = tmp_path / "r.jsonl"
    primary = f"/sdcard/Android/data/{PKG}/files/flowdiagram/runs/r.jsonl"
    fallback = f"/sdcard/Download/flowdiagram/{PKG}/r.jsonl"

    def pull_ok(cmd):
        dest.write_text("x")

    runner.when(f"pull {primary}", returncode=1, stderr="does not exist")
    runner.when(f"pull {fallback}", effect=pull_ok)
    assert p.fetch("r", dest) == dest
    pulls = [l for l in runner.lines() if " pull " in l]
    assert pulls == [f"adb -s RFCXB13QAVF pull {primary} {dest}", f"adb -s RFCXB13QAVF pull {fallback} {dest}"]
    # the successful location is tried first from now on, and discard removes both candidates
    assert p.remote_paths("r")[0] == fallback
    p.discard("r")
    assert runner.lines()[-1] == f"adb -s RFCXB13QAVF shell rm -f {fallback} {primary}"


def _fetch_with(p, runner, tmp_path, ok_path):
    dest = tmp_path / "r.jsonl"
    runner.when(f"pull {ok_path}", effect=lambda cmd: dest.write_text("x"))
    runner.when(" pull ", returncode=1)
    p.fetch("r", dest)
    p.fetch("r", dest)  # a second poll must not print again


def test_android_fetch_reports_primary_once(tmp_path, capsys):
    p, runner = ready_android()
    capsys.readouterr()
    primary = f"/sdcard/Android/data/{PKG}/files/flowdiagram/runs/r.jsonl"
    _fetch_with(p, runner, tmp_path, primary)
    out = capsys.readouterr().out
    assert out.count("Run file fetched from Android/data: " + primary) == 1
    assert "Download" not in out


def test_android_fetch_reports_forced_downloads(tmp_path, capsys):
    p, runner = ready_android(sink="downloads")
    capsys.readouterr()
    fallback = f"/sdcard/Download/flowdiagram/{PKG}/r.jsonl"
    _fetch_with(p, runner, tmp_path, fallback)
    out = capsys.readouterr().out
    assert out.count("Run file fetched from Download: " + fallback) == 1
    assert "fell back" not in out


def test_android_fetch_reports_auto_fallback(tmp_path, capsys):
    p, runner = ready_android()
    capsys.readouterr()
    fallback = f"/sdcard/Download/flowdiagram/{PKG}/r.jsonl"
    _fetch_with(p, runner, tmp_path, fallback)
    out = capsys.readouterr().out
    assert out.count("Run file fetched from Download: " + fallback) == 1
    assert out.count("primary path") == 1 and "fell back" in out


def test_android_fetch_missing_raises(tmp_path):
    p, runner = ready_android()
    runner.when(" pull ", returncode=1)
    with pytest.raises(RunFileNotFound):
        p.fetch("r", tmp_path / "r.jsonl")


# ---- iOS simulator
SIM_LIST = json.dumps({"devices": {"iOS-18-3": [
    {"udid": "SIM-1", "name": "iPhone 16 Pro", "state": "Booted"},
    {"udid": "SIM-2", "name": "iPhone 17", "state": "Shutdown"}]}})


def test_ios_simulator_validate_launch_fetch_stop(tmp_path):
    container = tmp_path / "container"
    runs = container / "Documents" / "flowdiagram" / "runs"
    runs.mkdir(parents=True)
    runner = FakeRunner().when("list devices booted", SIM_LIST).when("get_app_container", f"{container}\n")
    p = IosSimulatorPlatform(make_params(platform="ios_simulator"), runner)
    p.validate()
    assert p.udid == "SIM-1" and p.emulated

    p.launch("rid-1")
    assert runner.lines()[-1] == ("xcrun simctl launch --terminate-running-process SIM-1 org.example.App "
                                  "--flowDiagramFlag --flowDiagramRunId rid-1")
    with pytest.raises(RunFileNotFound):
        p.fetch("rid-1", tmp_path / "out.jsonl")
    (runs / "rid-1.jsonl").write_text("data")
    assert p.fetch("rid-1", tmp_path / "out.jsonl").read_text() == "data"
    p.discard("rid-1")
    assert not (runs / "rid-1.jsonl").exists()
    p.stop()
    assert runner.lines()[-1] == "xcrun simctl terminate SIM-1 org.example.App"


def test_ios_simulator_validate_errors():
    two = json.dumps({"devices": {"r": [{"udid": "A", "name": "a", "state": "Booted"},
                                        {"udid": "B", "name": "b", "state": "Booted"}]}})
    with pytest.raises(PlatformError, match="--udid"):
        IosSimulatorPlatform(make_params(), FakeRunner().when("list devices", two)).validate()
    with pytest.raises(PlatformError, match="not installed"):
        IosSimulatorPlatform(make_params(), FakeRunner().when("list devices", SIM_LIST)
                             .when("get_app_container", returncode=1)).validate()


# ---- iOS device
DEVICES = json.dumps({"result": {"devices": [
    {"identifier": "CORE-1", "hardwareProperties": {"udid": "UDID-1", "reality": "physical"},
     "deviceProperties": {"name": "iPhone"}},
    {"identifier": "SIM", "hardwareProperties": {"udid": "SIM", "reality": "simulated"}, "deviceProperties": {}}]}})
APPS = json.dumps({"result": {"apps": [{"bundleIdentifier": "org.example.App"}]}})
LAUNCHED = json.dumps({"result": {"process": {"processIdentifier": 4242}}})


def ios_device(runner, **over):
    return IosDevicePlatform(make_params(platform="ios_device", **over), runner)


def test_ios_device_validate_launch_fetch_stop(tmp_path):
    runner = FakeRunner().when("list devices", DEVICES).when("info apps", APPS).when("process launch", LAUNCHED)
    p = ios_device(runner)
    p.validate()
    assert p.udid == "UDID-1" and not p.emulated

    p.launch("rid-1")
    assert runner.lines()[-1] == (
        "xcrun devicectl device process launch -q --json-output - --terminate-existing --device UDID-1 "
        "org.example.App -- --flowDiagramFlag --flowDiagramRunId rid-1")

    dest = tmp_path / "out.jsonl"
    runner.when("copy from", returncode=1, stderr="no such file")
    with pytest.raises(RunFileNotFound):
        p.fetch("rid-1", dest)
    runner.rules.pop()
    runner.when("copy from", effect=lambda cmd: dest.write_text("x"))
    p.fetch("rid-1", dest)
    assert runner.lines()[-1] == (
        "xcrun devicectl device copy from --device UDID-1 --domain-type appDataContainer "
        f"--domain-identifier org.example.App --source Documents/flowdiagram/runs/rid-1.jsonl --destination {dest}")

    p.stop()
    assert runner.lines()[-1] == "xcrun devicectl device process terminate --device UDID-1 --pid 4242"


def test_ios_device_validate_errors():
    with pytest.raises(PlatformError, match="--udid"):
        two = json.loads(DEVICES)
        two["result"]["devices"].append({"identifier": "C2", "hardwareProperties": {"udid": "U2", "reality": "physical"},
                                         "deviceProperties": {}})
        ios_device(FakeRunner().when("list devices", json.dumps(two))).validate()
    with pytest.raises(PlatformError, match="not installed"):
        ios_device(FakeRunner().when("list devices", DEVICES).when("info apps", json.dumps({"result": {"apps": []}}))
                   ).validate()
    with pytest.raises(PlatformError, match="launch failed"):
        p = ios_device(FakeRunner().when("process launch", returncode=1, stderr="trust missing"), udid="U")
        p.launch("r")


def test_ios_device_launch_locked_reports_locked():
    stderr = "NSLocalizedFailureReason = Unable to launch X because the device was not, or could not be, unlocked."
    p = ios_device(FakeRunner().when("process launch", returncode=1, stderr=stderr), udid="U")
    with pytest.raises(PlatformError, match="iOS device U is locked"):
        p.launch("r")


def test_auto_picks_only_ready_target():
    runner = FakeRunner().when("adb devices", "List of devices attached\n") \
        .when("list devices booted", json.dumps({"devices": {}})) \
        .when("list devices", DEVICES).when("info apps", APPS)
    assert create_platform(make_params(platform="auto"), runner).name == "ios_device"
    with pytest.raises(PlatformError, match="No target is ready"):
        create_platform(make_params(platform="auto"), FakeRunner().when("list devices", json.dumps(
            {"result": {"devices": []}})))


ADB_TWO = "List of devices attached\nemulator-5554\tdevice\nRFCXB13QAVF\tdevice\n\n"
NO_SIM = json.dumps({"devices": {}})
ONE_SIM = json.dumps({"devices": {"iOS-18": [{"udid": "SIM-1", "name": "iPhone 16", "state": "Booted"}]}})
NO_DEVICES = json.dumps({"result": {"devices": []}})


def auto_runner(adb, sim=NO_SIM, devices=NO_DEVICES):
    return FakeRunner().when("adb devices", adb).when("pm list packages", f"package:{PKG}\n") \
        .when("list devices booted", sim).when("get_app_container", "/tmp/c") \
        .when("list devices", devices).when("info apps", APPS)


def test_auto_one_android_device_is_selected():
    assert create_platform(make_params(platform="auto"), auto_runner(ADB_ONE)).name == "android"


def test_auto_several_android_devices_lists_serials_and_flag():
    with pytest.raises(PlatformError) as e:
        create_platform(make_params(platform="auto"), auto_runner(ADB_TWO))
    msg = str(e.value)
    assert "android (emulator-5554, RFCXB13QAVF; pass --platform android --serial <id>)" in msg


def test_auto_android_plus_ios_lists_every_target():
    with pytest.raises(PlatformError) as e:
        create_platform(make_params(platform="auto"), auto_runner(ADB_TWO, sim=ONE_SIM, devices=DEVICES))
    msg = str(e.value)
    assert "android (emulator-5554, RFCXB13QAVF; pass --platform android --serial <id>)" in msg
    assert "ios_simulator (pass --platform ios_simulator)" in msg
    assert "ios_device (pass --platform ios_device)" in msg


def test_auto_several_ios_simulators_need_udid():
    two = json.dumps({"devices": {"iOS-18": [{"udid": "S1", "name": "A", "state": "Booted"},
                                              {"udid": "S2", "name": "B", "state": "Booted"}]}})
    with pytest.raises(PlatformError, match=r"ios_simulator \(S1, S2; pass --platform ios_simulator --udid <id>\)"):
        create_platform(make_params(platform="auto"), auto_runner("List of devices attached\n", sim=two))


def test_auto_nothing_ready():
    with pytest.raises(PlatformError, match="No target is ready"):
        create_platform(make_params(platform="auto"), auto_runner("List of devices attached\n"))
