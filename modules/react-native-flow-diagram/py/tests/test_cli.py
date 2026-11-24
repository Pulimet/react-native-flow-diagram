import pytest

from cli.cli_args import parse_args


def test_defaults_and_v2_flags():
    p = parse_args([])
    assert (p.platform, p.compile_mode, p.t0, p.wait_time, p.launch_times) == ("android", "speed-profile", "process_start", 10, 1)
    assert p.csv_path.endswith(".csv") and p.raw_dir.endswith("/raw")
    p = parse_args(["--platform", "ios_device", "--udid", "U", "--launch-times", "5", "--t0", "app_init",
                    "--compile-mode", "none", "--from-dir", "raw", "--serial", "S", "--wait_time", "3"])
    assert (p.udid, p.launch_times, p.t0, p.compile_mode, p.from_dir, p.serial, p.wait_time) == (
        "U", 5, "app_init", "none", "raw", "S", 3)


def test_extra_is_a_deprecated_noop(capsys):
    assert parse_args(["--extra", "True"]).platform == "android"
    assert "deprecated" in capsys.readouterr().out


def test_invalid_values_exit():
    with pytest.raises(SystemExit):
        parse_args(["--compile-mode", "fast"])
    with pytest.raises(SystemExit):
        parse_args(["--launch_times", "0"])
