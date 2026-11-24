from pathlib import Path

from platforms.base import (
    IOS_FLAG_ARG, IOS_RUN_ID_ARG, RUN_DIR_NAME, Platform, PlatformError, RunFileNotFound, error_text,
    parse_json_output, run_command,
)


class IosDevicePlatform(Platform):
    """Physical iPhone through devicectl. Needs a Release build with Development signing."""

    name = "ios_device"

    def __init__(self, params, runner=run_command):
        super().__init__(params, runner)
        self.udid = params.udid
        self._pid = None

    def devicectl(self, *args, timeout=120):
        return self.run(["xcrun", "devicectl", *args], timeout=timeout)

    def devicectl_json(self, *args, timeout=60):
        result = self.devicectl(*args, "-q", "--json-output", "-", timeout=timeout)
        if result.returncode != 0:
            raise PlatformError(f"devicectl {' '.join(args[:3])} failed: {error_text(result)}")
        return parse_json_output(result.stdout)

    def validate(self):
        devices = self.devicectl_json("list", "devices", timeout=30)["result"]["devices"]
        physical = [d for d in devices if d.get("hardwareProperties", {}).get("reality") == "physical"]
        names = {d["hardwareProperties"].get("udid") or d["identifier"]: d.get("deviceProperties", {}).get("name", "")
                 for d in physical}
        if self.udid:
            if self.udid not in names and not any(d["identifier"] == self.udid for d in physical):
                raise PlatformError(f"iOS device {self.udid} was not found. Known: {list(names) or 'none'}")
        elif len(names) != 1:
            hint = "Connect and unlock a device." if not names else \
                "Several devices are known (" + ", ".join(f"{n} {u}" for u, n in names.items()) + \
                "). Pick one with --udid."
            raise PlatformError(f"Expected exactly one physical iOS device. {hint}")
        else:
            self.udid = next(iter(names))

        bundle = self.params.bundle_id
        apps = self.devicectl_json("device", "info", "apps", "--device", self.udid, "--bundle-id", bundle)
        if not apps["result"].get("apps"):
            raise PlatformError(f"'{bundle}' is not installed on {self.udid}. Install the Release build with "
                                "'xcrun devicectl device install app' (never uninstall, it drops developer trust).")
        print(f"iOS device target: {names.get(self.udid, '')} {self.udid}, bundle {bundle}")

    def label(self):
        return f"ios device {self.udid or ''}".strip()

    def prepare(self):
        # Run files cannot be deleted through devicectl. The app keeps the newest 20 and run ids are unique.
        print("iOS device: screen lock cannot be changed from the host. Keep the phone unlocked.")

    def launch(self, run_id):
        result = self.devicectl(
            "device", "process", "launch", "-q", "--json-output", "-", "--terminate-existing",
            "--device", self.udid, self.params.bundle_id, "--", IOS_FLAG_ARG, IOS_RUN_ID_ARG, run_id)
        if result.returncode != 0:
            raise PlatformError(f"devicectl launch failed (phone locked or developer trust missing?): "
                                f"{error_text(result)}")
        try:
            self._pid = parse_json_output(result.stdout)["result"]["process"]["processIdentifier"]
        except (PlatformError, KeyError, TypeError):
            self._pid = None
        return {}

    def fetch(self, run_id, dest):
        dest = Path(dest)
        result = self.devicectl(
            "device", "copy", "from", "--device", self.udid, "--domain-type", "appDataContainer",
            "--domain-identifier", self.params.bundle_id,
            "--source", f"Documents/{RUN_DIR_NAME}/runs/{run_id}.jsonl", "--destination", str(dest), timeout=120)
        if result.returncode != 0 or not dest.exists():
            raise RunFileNotFound(f"devicectl copy failed: {error_text(result)}")
        return dest

    def stop(self):
        if self._pid is not None:
            self.devicectl("device", "process", "terminate", "--device", self.udid, "--pid", str(self._pid),
                           timeout=30)
            self._pid = None
