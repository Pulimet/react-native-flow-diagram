import argparse
from datetime import datetime
from dataclasses import dataclass


# bundle_id - You can find this in Xcode under Target > General > Identity > Bundle Identifier.

def parse_args():
    parser = argparse.ArgumentParser(description="Measurement script")
    parser.add_argument('--platform', choices=['android', 'ios_device', 'ios_simulator'], default='android', help='Platform to run measurements on. (Default: android)')
    parser.add_argument('--output-dir', type=str, default='output', help='Directory to save results. (Default: output)')
    parser.add_argument('--bundle_id', type=str, default='org.reactjs.native.example.FlowDiagram', help='iOS Bundle ID. (Default: org.reactjs.native.example.FlowDiagram)')
    parser.add_argument('--wait_time', type=int, default=10, help='Wait time after app launch in seconds. (Default: 10)')
    parser.add_argument('--launch_times', type=int, default=1, help='How many times to launch the app. (Default: 1)')
    parser.add_argument('--package', type=str, default='com.flowdiagram', help='Android package name. (Default: com.flowdiagram)')
    parser.add_argument('--activity', type=str, default='com.flowdiagram.MainActivity', help='Android activity full name. (Default: com.flowdiagram.MainActivity)')
    parser.add_argument('--extra', type=bool, default=False, help='Extra Intent / Bundle Settings (Default: False)')
    parser.add_argument('--open_csv', type=bool, default=False, help='Should open CSV with results (Default: False)')
    parser.add_argument('--open_png', type=bool, default=False, help='Extra Should open PNG with results (Default: False)')

    args = parser.parse_args()

    print("Measurement script launched with arguments: " + ", ".join(
        f"\033[1m{name}\033[0m: {value}" for name, value in vars(args).items()
    ))

    # Create output paths and file names
    date = datetime.now().strftime('%y-%m-%d')
    output_path = f"{args.output_dir}/{date}"
    file_name_prefix = "measure"
    date_time = datetime.now().strftime('%y-%m-%d_%H-%M')
    file_name = f"{file_name_prefix}_{date_time}"
    file_path = f"{output_path}/{file_name}"

    csv_path = f"{file_path}.csv"
    csv_net_path = f"{file_path}_net.csv"
    png_path = f"{file_path}.png"

    return CLIParams(
        args.platform, args.package, args.extra, args.bundle_id, args.wait_time,args.activity, args.launch_times,
        csv_path, csv_net_path, png_path, args.output_dir, output_path, args.open_csv, args.open_png
    )

@dataclass
class CLIParams:
    platform: str
    package: str
    extra: bool
    bundle_id: str
    wait_time: int
    activity: str
    launch_times: int
    csv_path: str
    csv_net_path: str
    png_path: str
    output_dir: str
    output_path: str
    open_csv: bool
    open_png: bool
