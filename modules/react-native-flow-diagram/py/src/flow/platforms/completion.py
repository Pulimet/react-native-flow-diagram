import json
import time
from dataclasses import dataclass
from pathlib import Path

from platforms.base import Platform, PlatformError, RunFileNotFound


@dataclass
class WaitSettings:
    settle: float = 10.0  # minimum time after launch before the first fetch
    poll_interval: float = 1.0
    stable_polls: int = 2  # identical consecutive fetches that count as "app is done writing"
    timeout: float = 60.0  # hard limit measured from launch


def has_run_end(data: bytes) -> bool:
    lines = [l for l in data.decode("utf-8", errors="replace").splitlines() if l.strip()]
    if not lines:
        return False
    try:
        return json.loads(lines[-1]).get("type") == "run_end"
    except (ValueError, AttributeError):
        return False


def wait_and_fetch(platform: Platform, run_id: str, dest: Path, settings: WaitSettings,
                   sleep=time.sleep, clock=time.monotonic) -> Path:
    """Wait for the app to finish recording, then return the pulled run file.

    The app does not always write run_end, so a run counts as complete when run_end is the last line, or when
    the pulled file stayed identical for `stable_polls` polls. After `timeout` seconds a partial file is
    returned with a warning; no file at all is an error.
    """
    start = clock()
    sleep(settings.settle)
    last = None
    stable = 0
    last_error = ""
    while True:
        data = None
        try:
            data = platform.fetch(run_id, dest).read_bytes()
        except RunFileNotFound as e:
            last_error = str(e)

        if data:
            if has_run_end(data):
                return dest
            stable = stable + 1 if data == last else 0
            if stable >= settings.stable_polls:
                return dest
            last = data

        if clock() - start >= settings.timeout:
            if data:
                print(f"WARNING: {run_id} was still changing after {settings.timeout:g}s, using the partial file")
                return dest
            raise PlatformError(
                f"no run file after {settings.timeout:g}s ({last_error}). Is the app a build with the v2 recorder, "
                "is the package/bundle id right, and did the launch reach the first activity?")
        sleep(settings.poll_interval)
