import json
import shutil
from pathlib import Path

from platforms.base import (
    IOS_FLAG_ARG, IOS_RUN_ID_ARG, RUN_DIR_NAME, Platform, PlatformError, RunFileNotFound, AmbiguousTarget, error_text,
    run_command,
)

BOOTED = "booted"


class IosSimulatorPlatform(Platform):
    """Simulator through simctl. The app data container is a plain macOS directory."""

    name = "ios_simulator"
    emulated = True

    def __init__(self, params, runner=run_command):
        super().__init__(params, runner)
        self.udid = params.udid
        self._container = None

    def simctl(self, *args, timeout=60):
        return self.run(["xcrun", "simctl", *args], timeout=timeout)

    def validate(self):
        result = self.simctl("list", "devices", BOOTED, "--json", timeout=30)
        if result.returncode != 0:
            raise PlatformError(f"'simctl list devices' failed: {error_text(result)}")
        try:
            groups = json.loads(result.stdout).get("devices", {})
        except ValueError as e:
            raise PlatformError("could not parse 'simctl list devices' output") from e
        booted = [d for devices in groups.values() for d in devices if d.get("state") == "Booted"]
        udids = {d["udid"]: d.get("name", "") for d in booted}
        if self.udid:
            if self.udid not in udids:
                raise PlatformError(f"Simulator {self.udid} is not booted. Booted: {list(udids) or 'none'}")
        elif not udids:
            raise PlatformError("Expected exactly one booted iOS simulator. Boot a simulator first.")
        elif len(udids) > 1:
            raise AmbiguousTarget(
                "Expected exactly one booted iOS simulator. Several simulators are booted ("
                + ", ".join(f"{n} {u}" for u, n in udids.items()) + "). Pick one with --udid.",
                "--udid", list(udids))
        else:
            self.udid = next(iter(udids))
        bundle = self.params.bundle_id
        if self.simctl("get_app_container", self.udid, bundle, "data", timeout=30).returncode != 0:
            raise PlatformError(f"'{bundle}' is not installed on simulator {self.udid}. "
                                "Install the Release build with 'xcrun simctl install'.")
        print(f"iOS simulator target: {udids.get(self.udid, '')} {self.udid}, bundle {bundle}")

    def label(self):
        return f"ios simulator {self.udid or ''}".strip()

    def container(self) -> Path:
        if self._container is None:
            result = self.simctl("get_app_container", self.udid, self.params.bundle_id, "data", timeout=30)
            if result.returncode != 0:
                raise PlatformError(f"get_app_container failed: {error_text(result)}")
            self._container = Path(result.stdout.strip())
        return self._container

    def runs_dir(self) -> Path:
        return self.container() / "Documents" / RUN_DIR_NAME / "runs"

    def prepare(self):
        for old in self.runs_dir().glob("*.jsonl"):
            old.unlink(missing_ok=True)
        self.stop()

    def launch(self, run_id):
        result = self.simctl("launch", "--terminate-running-process", self.udid, self.params.bundle_id,
                             IOS_FLAG_ARG, IOS_RUN_ID_ARG, run_id)
        if result.returncode != 0:
            raise PlatformError(f"simctl launch failed: {error_text(result)}")
        self._container = None  # a reinstall between runs changes the container
        return {}

    def fetch(self, run_id, dest):
        src = self.runs_dir() / f"{run_id}.jsonl"
        if not src.exists():
            raise RunFileNotFound(f"{src} does not exist")
        shutil.copyfile(src, dest)
        return Path(dest)

    def stop(self):
        self.simctl("terminate", self.udid, self.params.bundle_id, timeout=30)

    def discard(self, run_id):
        (self.runs_dir() / f"{run_id}.jsonl").unlink(missing_ok=True)
