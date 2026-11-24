import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from events.normalize import normalize
from events.reader import RunFileError, read_run
from platforms.base import Platform, PlatformError
from platforms.completion import WaitSettings, wait_and_fetch

MISSING_RUN_END = "run_end is missing"


class FatalRunError(Exception):
    """Stop the whole loop: repeating the launch will not help."""


@dataclass
class Measurement:
    entries: list = field(default_factory=list)  # v1-shaped dicts of all successful runs
    runs: list = field(default_factory=list)  # headers of the successful runs
    failures: list = field(default_factory=list)
    launch_metrics: list = field(default_factory=list)
    effective_t0: str = ""


def new_run_id(index: int, now=None) -> str:
    return f"{(now or datetime.now()).strftime('%Y%m%d-%H%M%S')}-it{index:02d}"


def settings_from(params) -> WaitSettings:
    return WaitSettings(settle=params.wait_time, poll_interval=params.poll_interval,
                        stable_polls=params.stable_polls, timeout=params.timeout)


def ingest(path, run_id, params, result: Measurement):
    """Read and normalize one raw file into the result. Raises RunFileError for unusable files."""
    run = read_run(path, expected_run_id=run_id)
    header = run.header
    if (header.debuggable or header.build == "debug") and not params.allow_debuggable:
        raise FatalRunError(f"{run_id}: the app reports a debuggable/debug build. Measure a release build, "
                            "or pass --allow-debuggable.")
    out = normalize(run, t0=params.t0)
    for warning in out.warnings:
        if not warning.startswith(MISSING_RUN_END):
            print(f"  warning: {warning}")
    result.entries.extend(out.entries)
    result.runs.append(header)
    result.effective_t0 = out.effective_t0


def start_measurements(platform: Platform, params, sleep=time.sleep, clock=time.monotonic) -> Measurement:
    print(f"Launching and collecting data {params.launch_times} times...")
    raw_dir = Path(params.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    settings = settings_from(params)
    result = Measurement()

    for i in range(1, params.launch_times + 1):
        run_id = new_run_id(i)
        print(f"Iteration {i}/{params.launch_times} (run id {run_id})")
        dest = raw_dir / f"{run_id}.jsonl"
        try:
            metrics = platform.launch(run_id)
            wait_and_fetch(platform, run_id, dest, settings, sleep=sleep, clock=clock)
            # Pull before stopping so a force-stop cannot lose the tail of the file.
            platform.stop()
            ingest(dest, run_id, params, result)
            if metrics:
                result.launch_metrics.append(metrics)
            platform.discard(run_id)
        except (PlatformError, RunFileError) as e:
            print(f"  run {run_id} failed: {e}")
            result.failures.append(f"{run_id}: {e}")
            try:
                platform.stop()
            except PlatformError:
                pass
    return result


def load_from_dir(directory, params) -> Measurement:
    files = sorted(Path(directory).glob("*.jsonl"))
    if not files:
        raise PlatformError(f"no *.jsonl run files in {directory}")
    result = Measurement()
    for path in files:
        try:
            ingest(path, None, params, result)
        except RunFileError as e:
            print(f"  skipped {path.name}: {e}")
            result.failures.append(f"{path.name}: {e}")
    return result


def report_meta(result: Measurement, platform=None) -> dict:
    first = result.runs[0]
    meta = {
        "runs": len(result.runs), "device": first.device, "os": first.os, "build": first.build,
        "app_version": first.app_version, "t0": result.effective_t0,
        "note": platform.note() if platform else "",
    }
    totals = [m["total_time_ms"] for m in result.launch_metrics if "total_time_ms" in m]
    if totals:
        meta["system_total_time_ms"] = int(sum(totals) / len(totals))
    return meta
