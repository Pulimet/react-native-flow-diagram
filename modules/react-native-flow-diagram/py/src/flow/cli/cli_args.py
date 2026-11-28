import argparse
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# bundle_id - You can find this in Xcode under Target > General > Identity > Bundle Identifier.

COMPILE_MODES = ["speed-profile", "speed", "verify", "none"]


def build_parser():
    p = argparse.ArgumentParser(
        description="Measure app startup flows from the v2 run files that the FlowDiagram recorder writes.")
    p.add_argument('--platform', choices=['android', 'ios_device', 'ios_simulator', 'auto'], default='android',
                   help="Target. 'auto' picks the only ready target. (Default: android)")
    p.add_argument('--output-dir', '--output_dir', dest='output_dir', default='output',
                   help='Directory to save results. (Default: output)')
    p.add_argument('--launch_times', '--launch-times', dest='launch_times', type=int, default=1,
                   help='How many times to launch the app. (Default: 1)')

    app = p.add_argument_group('app')
    app.add_argument('--package', default='com.flowdiagram', help='Android package name. (Default: com.flowdiagram)')
    app.add_argument('--activity', default='com.flowdiagram.MainActivity',
                     help='Android activity full name. (Default: com.flowdiagram.MainActivity)')
    app.add_argument('--bundle_id', '--bundle-id', dest='bundle_id', default='org.reactjs.native.example.FlowDiagram',
                     help='iOS Bundle ID. (Default: org.reactjs.native.example.FlowDiagram)')

    dev = p.add_argument_group('device selection')
    dev.add_argument('--serial', help='adb serial, needed when several Android devices are connected.')
    dev.add_argument('--udid', help='iOS device or simulator UDID, needed when several are available.')

    meas = p.add_argument_group('measurement')
    meas.add_argument('--compile-mode', dest='compile_mode', choices=COMPILE_MODES, default='speed-profile',
                      help="Android dexopt mode applied before measuring; 'none' keeps the current state. "
                           "(Default: speed-profile)")
    meas.add_argument('--t0', choices=['process_start', 'app_init'], default='process_start',
                      help="Time origin. 'app_init' gives v1 comparable numbers. (Default: process_start)")
    meas.add_argument('--sink', choices=['auto', 'downloads'], default='auto',
                      help="Android run file location. 'auto' uses Android/data and falls back to Download; "
                           "'downloads' asks the app to write to Download. (Default: auto)")
    meas.add_argument('--allow-debuggable', dest='allow_debuggable', action='store_true',
                      help='Measure a debuggable/debug build anyway (numbers are not representative).')
    meas.add_argument('--strip-query', '--strip_query', dest='strip_query', action='append', default=[],
                      metavar='PATTERN',
                      help='Drop the query string of network URLs whose address (before "?") contains PATTERN, '
                           'so they are averaged as one request. Repeat the flag or separate patterns with commas.')

    wait = p.add_argument_group('completion detection')
    wait.add_argument('--wait_time', '--wait-time', dest='wait_time', type=float, default=10,
                      help='Seconds to wait after launch before the first fetch. (Default: 10)')
    wait.add_argument('--poll-interval', dest='poll_interval', type=float, default=1.0,
                      help='Seconds between fetches after the settle time. (Default: 1)')
    wait.add_argument('--stable-polls', dest='stable_polls', type=int, default=2,
                      help='Identical consecutive fetches that mean the run is complete when run_end is '
                           'missing. (Default: 2)')
    wait.add_argument('--timeout', type=float, default=60,
                      help='Hard limit in seconds per run, measured from launch. (Default: 60)')

    src = p.add_argument_group('offline')
    src.add_argument('--from-dir', dest='from_dir',
                     help='Build the reports from saved *.jsonl run files in this directory, no device needed.')

    out = p.add_argument_group('output')
    out.add_argument('--open_csv', '--open-csv', dest='open_csv', type=bool, default=False,
                     help='Should open CSV with results (Default: False)')
    out.add_argument('--open_png', '--open-png', dest='open_png', type=bool, default=False,
                     help='Should open PNG with results (Default: False)')
    out.add_argument('--open_html', '--open-html', dest='open_html', type=bool, default=False,
                     help='Should open the interactive HTML report in the browser (Default: False)')
    p.add_argument('--extra', default=None, help=argparse.SUPPRESS)  # v1 flag, now a no-op
    return p


def parse_args(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.extra is not None:
        print("WARNING: --extra is deprecated and ignored. The flag is always passed in v2.")
    if args.launch_times < 1:
        parser.error("--launch_times must be at least 1")
    args.strip_query = tuple(p.strip() for value in args.strip_query for p in value.split(',') if p.strip())

    print("Measurement script launched with arguments: " + ", ".join(
        f"\033[1m{name}\033[0m: {value}" for name, value in vars(args).items()
    ))

    # Create output paths and file names
    now = datetime.now()
    output_path = f"{args.output_dir}/{now.strftime('%y-%m-%d')}"
    file_path = f"{output_path}/measure_{now.strftime('%y-%m-%d_%H-%M')}"

    return CLIParams(
        platform=args.platform, package=args.package, bundle_id=args.bundle_id, activity=args.activity,
        wait_time=args.wait_time, launch_times=args.launch_times, serial=args.serial, udid=args.udid,
        compile_mode=args.compile_mode, t0=args.t0, sink=args.sink, allow_debuggable=args.allow_debuggable,
        strip_query=args.strip_query,
        poll_interval=args.poll_interval, stable_polls=args.stable_polls, timeout=args.timeout,
        from_dir=args.from_dir, csv_path=f"{file_path}.csv", csv_net_path=f"{file_path}_net.csv",
        png_path=f"{file_path}.png", svg_path=f"{file_path}.svg", html_path=f"{file_path}.html", raw_dir=f"{output_path}/raw", output_dir=args.output_dir,
        output_path=output_path, open_csv=args.open_csv, open_png=args.open_png,
        open_html=args.open_html,
    )


@dataclass
class CLIParams:
    platform: str
    package: str
    bundle_id: str
    activity: str
    wait_time: float
    launch_times: int
    csv_path: str
    csv_net_path: str
    png_path: str
    svg_path: str
    html_path: str
    raw_dir: str
    output_dir: str
    output_path: str
    serial: Optional[str] = None
    udid: Optional[str] = None
    compile_mode: str = "speed-profile"
    t0: str = "process_start"
    sink: str = "auto"
    allow_debuggable: bool = False
    strip_query: tuple = ()
    poll_interval: float = 1.0
    stable_polls: int = 2
    timeout: float = 60.0
    from_dir: Optional[str] = None
    open_csv: bool = False
    open_png: bool = False
    open_html: bool = False
