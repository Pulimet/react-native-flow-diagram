import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "flow"))

import subprocess
from types import SimpleNamespace

import pytest


def make_params(**over):
    base = dict(platform="android", package="com.flowdiagram", bundle_id="org.example.App",
                activity="com.flowdiagram.MainActivity", serial=None, udid=None, compile_mode="speed-profile",
                sink="auto", allow_debuggable=False, wait_time=0, poll_interval=0, stable_polls=2, timeout=5,
                launch_times=3, t0="process_start", strip_query=())
    base.update(over)
    return SimpleNamespace(**base)


class FakeRunner:
    """Records every command. rules: list of (predicate on the joined command string, result or callable)."""

    def __init__(self, *rules):
        self.rules = list(rules)
        self.calls = []

    def when(self, needle, stdout="", returncode=0, stderr="", effect=None):
        self.rules.append((needle, stdout, returncode, stderr, effect))
        return self

    def __call__(self, cmd, timeout=None):
        cmd = [str(c) for c in cmd]
        self.calls.append(cmd)
        line = " ".join(cmd)
        for needle, stdout, rc, stderr, effect in self.rules:
            if needle in line:
                if effect:
                    effect(cmd)
                return subprocess.CompletedProcess(cmd, rc, stdout, stderr)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def lines(self):
        return [" ".join(c) for c in self.calls]


@pytest.fixture
def params():
    return make_params()
