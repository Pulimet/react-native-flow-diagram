import json
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

RUN_DIR_NAME = "flowdiagram"
LAUNCH_FLAG_NAME = "FlowDiagramFlag"
LAUNCH_RUN_ID_NAME = "FlowDiagramRunId"
IOS_FLAG_ARG = "--flowDiagramFlag"
IOS_RUN_ID_ARG = "--flowDiagramRunId"


class PlatformError(Exception):
    """A device, tool or app problem that the user has to fix."""


class AmbiguousTarget(PlatformError):
    """Several devices of this platform are ready and the user has to pick one with `flag`."""

    def __init__(self, message, flag, choices):
        super().__init__(message)
        self.flag = flag
        self.choices = choices  # list of "id" or "id name" strings


class RunFileNotFound(PlatformError):
    """The run file is not (yet) on the device. Normal while the app is still starting."""


def run_command(cmd, timeout: Optional[float] = 120) -> subprocess.CompletedProcess:
    """The only place that starts host processes. Tests replace it with a fake."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise PlatformError(f"'{cmd[0]}' was not found on PATH ({e})") from e
    except subprocess.TimeoutExpired as e:
        raise PlatformError(f"command timed out after {timeout}s: {' '.join(map(str, cmd))}") from e


def parse_json_output(stdout: str):
    """devicectl prints pure JSON with -q --json-output -. Tolerate leading table text."""
    try:
        return json.loads(stdout)
    except ValueError:
        pass
    start = stdout.find("\n{")
    if start >= 0:
        try:
            return json.loads(stdout[start + 1:])
        except ValueError:
            pass
    raise PlatformError("could not parse JSON output of the device tool")


def error_text(result) -> str:
    lines = (result.stderr or result.stdout or "").strip().splitlines()
    return lines[-1] if lines else f"exit code {result.returncode}"


class Platform(ABC):
    """One measurement target. All methods are synchronous and raise PlatformError."""

    name = ""
    # Emulators and simulators are functional checks only, the report is labeled accordingly.
    emulated = False

    def __init__(self, params, runner=run_command):
        self.params = params
        self.run = runner

    @abstractmethod
    def validate(self) -> None:
        """Resolve the device, check the app is installed and that it is not a debug build when detectable."""

    @abstractmethod
    def prepare(self) -> None:
        """One-time setup before the first launch (compile mode, remove old run files, keep screen on)."""

    @abstractmethod
    def launch(self, run_id: str) -> dict:
        """Cold start the app with the flag and run id. Returns extra launch metrics (may be empty)."""

    @abstractmethod
    def fetch(self, run_id: str, dest: Path) -> Path:
        """One attempt to copy the run file to dest. Raises RunFileNotFound when it does not exist yet."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the app. Called after the run file was pulled."""

    def discard(self, run_id: str) -> None:
        """Remove the run file from the device when the platform has no retention of its own."""

    def cleanup(self) -> None:
        """Undo prepare (screen timeout) and stop the app."""
        self.stop()

    def label(self) -> str:
        return self.name

    def note(self) -> str:
        return "functional, not representative (emulator/simulator)" if self.emulated else ""

    def check(self, cmd, what: str, timeout: Optional[float] = 120):
        result = self.run(cmd, timeout=timeout)
        if result.returncode != 0:
            raise PlatformError(f"{what} failed: {error_text(result)}")
        return result
