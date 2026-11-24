#!/usr/bin/env python3
"""Phase 0 spike: launch the app with the FlowDiagram flag, fetch the run file, verify run_start.

Standard library only.
  python3 phase0_fetch.py --target android
  python3 phase0_fetch.py --target android_downloads
  python3 phase0_fetch.py --target ios_simulator
  python3 phase0_fetch.py --target ios_device --udid <udid>
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ANDROID_PKG = "com.flowdiagram"
ANDROID_ACTIVITY = "com.flowdiagram.MainActivity"
IOS_BUNDLE = "org.reactjs.native.example.FlowDiagram"


def run(cmd, check=True):
    print("$ " + " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.stderr.strip():
        print(r.stderr.strip(), file=sys.stderr)
    if check and r.returncode != 0:
        sys.exit(f"command failed ({r.returncode})")
    return r


def fetch(args, run_id, dest: Path) -> Path:
    local = dest / f"{run_id}.jsonl"
    if args.target in ("android", "android_downloads"):
        adb = ["adb"] + (["-s", args.serial] if args.serial else [])
        extra = ["--es", "FlowDiagramSink", "downloads"] if args.target == "android_downloads" else []
        run(adb + ["shell", "am", "start", "-W", "-S", "-n", f"{ANDROID_PKG}/{ANDROID_ACTIVITY}",
                   "--ez", "FlowDiagramFlag", "true", "--es", "FlowDiagramRunId", run_id] + extra)
        time.sleep(args.wait)
        if args.target == "android":
            remote = f"/sdcard/Android/data/{ANDROID_PKG}/files/flowdiagram/runs/{run_id}.jsonl"
        else:
            remote = f"/sdcard/Download/flowdiagram/{ANDROID_PKG}/{run_id}.jsonl"
        run(adb + ["pull", remote, str(local)])
    elif args.target == "ios_simulator":
        run(["xcrun", "simctl", "launch", "--terminate-running-process", "booted", args.bundle,
             "--flowDiagramFlag", "--flowDiagramRunId", run_id])
        time.sleep(args.wait)
        container = run(["xcrun", "simctl", "get_app_container", "booted", args.bundle, "data"]).stdout.strip()
        src = Path(container) / "Documents" / "flowdiagram" / "runs" / f"{run_id}.jsonl"
        local.write_bytes(src.read_bytes())
    elif args.target == "ios_device":
        if not args.udid:
            sys.exit("--udid is required for ios_device")
        run(["xcrun", "devicectl", "device", "process", "launch", "--terminate-existing",
             "--device", args.udid, args.bundle, "--", "--flowDiagramFlag", "--flowDiagramRunId", run_id])
        time.sleep(args.wait)
        run(["xcrun", "devicectl", "device", "copy", "from", "--device", args.udid,
             "--domain-type", "appDataContainer", "--domain-identifier", args.bundle,
             "--source", f"Documents/flowdiagram/runs/{run_id}.jsonl", "--destination", str(local)])
    return local


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", required=True,
                   choices=["android", "android_downloads", "ios_simulator", "ios_device"])
    p.add_argument("--bundle", default=IOS_BUNDLE, help="iOS bundle id")
    p.add_argument("--udid", help="iOS device UDID")
    p.add_argument("--serial", help="adb serial")
    p.add_argument("--wait", type=float, default=5.0, help="seconds to wait after launch")
    args = p.parse_args()

    run_id = uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory() as d:
        local = fetch(args, run_id, Path(d))
        text = local.read_text()
    print("--- fetched file ---")
    print(text)
    records = [json.loads(l) for l in text.splitlines() if l.strip()]
    ok = any(r.get("type") == "run_start" and r.get("runId") == run_id for r in records)
    print(f"RESULT {args.target}: {'PASS' if ok else 'FAIL'} (runId={run_id}, lines={len(records)})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
