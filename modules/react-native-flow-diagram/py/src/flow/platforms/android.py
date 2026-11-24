import re
import time
from pathlib import Path

from platforms.base import (
    LAUNCH_FLAG_NAME, LAUNCH_RUN_ID_NAME, RUN_DIR_NAME, Platform, PlatformError, RunFileNotFound, error_text, run_command,
)

SINK_EXTRA = "FlowDiagramSink"
SCREEN_TIMEOUT_KEY = "screen_off_timeout"
SCREEN_TIMEOUT_STAY_ON = "3600000"
SCREEN_TIMEOUT_DEFAULT = "300000"
COMPILE_MODES = ("speed-profile", "speed", "verify", "none")


class AndroidPlatform(Platform):
    """Emulator and physical device, both through adb."""

    name = "android"

    def __init__(self, params, runner=run_command):
        super().__init__(params, runner)
        self.serial = params.serial
        self._old_screen_timeout = None
        self._remote_hit = None  # which remote location last had the file

    # ---- paths
    @property
    def primary_dir(self):
        return f"/sdcard/Android/data/{self.params.package}/files/{RUN_DIR_NAME}/runs"

    @property
    def downloads_dir(self):
        return f"/sdcard/Download/{RUN_DIR_NAME}/{self.params.package}"

    def remote_paths(self, run_id):
        primary = f"{self.primary_dir}/{run_id}.jsonl"
        downloads = f"{self.downloads_dir}/{run_id}.jsonl"
        if self.params.sink == "downloads" or self._remote_hit == downloads:
            return [downloads, primary]
        return [primary, downloads]

    # ---- adb helpers
    def adb(self, *args):
        return ["adb"] + (["-s", self.serial] if self.serial else []) + list(args)

    def shell(self, *args, timeout=120):
        return self.run(self.adb("shell", *args), timeout=timeout)

    # ---- Platform
    def validate(self):
        result = self.run(["adb", "devices"], timeout=30)
        if result.returncode != 0:
            raise PlatformError(f"'adb devices' failed: {error_text(result)}")
        devices = []
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                devices.append((parts[0], parts[1]))
        ready = [serial for serial, state in devices if state == "device"]
        if self.serial:
            if self.serial not in ready:
                state = dict(devices).get(self.serial, "not connected")
                raise PlatformError(f"Android device {self.serial} is {state}. Connected: {ready or 'none'}")
        elif len(ready) != 1:
            hint = "Connect a device or start an emulator." if not ready else \
                f"Several devices are connected ({', '.join(ready)}). Pick one with --serial."
            raise PlatformError(f"Expected exactly one Android device. {hint}")
        else:
            self.serial = ready[0]
        self.emulated = self.serial.startswith("emulator-")

        pkg = self.params.package
        listed = self.shell("pm", "list", "packages", pkg, timeout=30)
        if f"package:{pkg}" not in listed.stdout.split():
            raise PlatformError(f"Package '{pkg}' is not installed on {self.serial}. Install the release APK first.")
        info = self.shell("dumpsys", "package", pkg, timeout=30).stdout
        if re.search(r"(?:pkgFlags|flags)=\[[^\]]*\bDEBUGGABLE\b", info) and not self.params.allow_debuggable:
            raise PlatformError(
                f"'{pkg}' is a debuggable build. Measure a release build, or pass --allow-debuggable.")
        print(f"Android target: {self.label()} ({self.serial}), package {pkg}")

    def label(self):
        return f"android {'emulator' if self.emulated else 'device'} {self.serial or ''}".strip()

    def prepare(self):
        pkg = self.params.package
        self.shell("input", "keyevent", "KEYCODE_WAKEUP", timeout=30)
        self.ensure_unlocked()
        current = self.shell("settings", "get", "system", SCREEN_TIMEOUT_KEY, timeout=30).stdout.strip()
        self._old_screen_timeout = current if current.isdigit() else SCREEN_TIMEOUT_DEFAULT
        self.shell("settings", "put", "system", SCREEN_TIMEOUT_KEY, SCREEN_TIMEOUT_STAY_ON, timeout=30)

        self.shell("rm", "-f", f"{self.primary_dir}/*.jsonl", f"{self.downloads_dir}/*.jsonl", timeout=30)

        mode = self.params.compile_mode
        if mode != "none":
            print(f"Compiling {pkg} with compile mode '{mode}'...")
            result = self.shell("cmd", "package", "compile", "-m", mode, "-f", pkg, timeout=600)
            if result.returncode != 0 or "Success" not in result.stdout:
                print(f"WARNING: compile mode '{mode}' was not applied: {error_text(result)}")
        else:
            print("Compile mode 'none': leaving the installed compilation state as is.")
        self.stop()

    def is_locked(self):
        out = self.shell("dumpsys", "window", timeout=30).stdout
        return "isKeyguardShowing=true" in out or "mDreamingLockscreen=true" in out

    def ensure_unlocked(self):
        """A locked screen delays or blocks the first activity. Dismiss a plain swipe lock, fail on a secure one."""
        if not self.is_locked():
            return
        self.shell("wm", "dismiss-keyguard", timeout=30)
        self.shell("input", "keyevent", "KEYCODE_MENU", timeout=30)
        time.sleep(1)
        if self.is_locked():
            raise PlatformError(f"Android device {self.serial} is locked. Unlock it (and keep it unlocked) and retry.")

    def launch(self, run_id):
        extras = ["--ez", LAUNCH_FLAG_NAME, "true", "--es", LAUNCH_RUN_ID_NAME, run_id]
        if self.params.sink == "downloads":
            extras += ["--es", SINK_EXTRA, "downloads"]
        self._remote_hit = None
        result = self.shell("am", "start", "-W", "-S", "-n", f"{self.params.package}/{self.params.activity}",
                            *extras)
        out = result.stdout + result.stderr
        if result.returncode != 0 or "Error" in out:
            raise PlatformError(f"am start failed: {out.strip() or result.returncode}")
        metrics = {}
        for key, field in (("TotalTime", "total_time_ms"), ("WaitTime", "wait_time_ms")):
            m = re.search(rf"{key}:\s*(\d+)", out)
            if m:
                metrics[field] = int(m.group(1))
        return metrics

    def fetch(self, run_id, dest):
        dest = Path(dest)
        for remote in self.remote_paths(run_id):
            result = self.run(self.adb("pull", remote, str(dest)), timeout=60)
            if result.returncode == 0 and dest.exists():
                self._remote_hit = remote
                return dest
        raise RunFileNotFound(f"{run_id}.jsonl not found in {self.primary_dir} or {self.downloads_dir}")

    def stop(self):
        self.shell("am", "force-stop", self.params.package, timeout=30)

    def discard(self, run_id):
        self.shell("rm", "-f", *self.remote_paths(run_id), timeout=30)

    def cleanup(self):
        if self._old_screen_timeout:
            self.shell("settings", "put", "system", SCREEN_TIMEOUT_KEY, self._old_screen_timeout, timeout=30)
        self.stop()
