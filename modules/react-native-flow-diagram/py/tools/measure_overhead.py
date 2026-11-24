"""Recorder overhead on Android: cold start with and without the FlowDiagram flag.

Launches are interleaved (off, on, off, on, ...) so thermal drift hits both sides equally. The metric is
`am start -W` TotalTime. Usage:
  python tools/measure_overhead.py --serial emulator-5554 --runs 10 [--package com.flowdiagram]
"""
import argparse
import re
import statistics
import subprocess
import time


def adb(serial, *args):
    return subprocess.run(["adb", "-s", serial, *args], capture_output=True, text=True, timeout=120).stdout


def launch(serial, package, activity, flagged):
    extras = ["--ez", "FlowDiagramFlag", "true", "--es", "FlowDiagramRunId", f"ovh-{int(time.time())}"] if flagged else []
    out = adb(serial, "shell", "am", "start", "-W", "-S", "-n", f"{package}/{activity}", *extras)
    m = re.search(r"TotalTime:\s*(\d+)", out)
    if not m:
        raise SystemExit(f"no TotalTime in output:\n{out}")
    return int(m.group(1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", required=True)
    ap.add_argument("--package", default="com.flowdiagram")
    ap.add_argument("--activity", default="com.flowdiagram.MainActivity")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--settle", type=float, default=6.0)
    ap.add_argument("--compile-mode", default="speed-profile")
    a = ap.parse_args()

    adb(a.serial, "shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb(a.serial, "shell", "cmd", "package", "compile", "-m", a.compile_mode, "-f", a.package)
    off, on = [], []
    for i in range(a.runs + 1):  # first pair warms caches and is dropped
        for flagged, bucket in ((False, off), (True, on)):
            t = launch(a.serial, a.package, a.activity, flagged)
            if i:
                bucket.append(t)
            time.sleep(a.settle)
    adb(a.serial, "shell", "am", "force-stop", a.package)

    def stats(xs):
        return statistics.mean(xs), statistics.median(xs), statistics.stdev(xs) if len(xs) > 1 else 0.0

    (m0, md0, s0), (m1, md1, s1) = stats(off), stats(on)
    print(f"off: {off}\non:  {on}")
    print(f"off mean {m0:.1f} ms, median {md0:.1f}, sd {s0:.1f}")
    print(f"on  mean {m1:.1f} ms, median {md1:.1f}, sd {s1:.1f}")
    print(f"overhead mean {(m1 - m0) / m0 * 100:+.2f}%  median {(md1 - md0) / md0 * 100:+.2f}%  ({m1 - m0:+.1f} ms)")


if __name__ == "__main__":
    main()
