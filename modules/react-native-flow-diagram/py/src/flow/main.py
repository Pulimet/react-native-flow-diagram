import sys
from pathlib import Path

from cli.cli_args import parse_args
from platforms import create_platform
from platforms.base import PlatformError
from report.calc_average import calculate_averages
from report.csv_utils import save_csv_with_data
from report.visualize import save_png_with_data
from run_loop import FatalRunError, load_from_dir, report_meta, start_measurements


def main(argv=None):
    print("----------------------- Measurement Script Started----------------------- ")
    params = parse_args(argv)
    try:
        if params.from_dir:
            print(f"----------------------- LOADING SAVED RUNS FROM {params.from_dir} -----------------------")
            result, platform = load_from_dir(params.from_dir, params), None
        else:
            result, platform = measure(params)
    except (PlatformError, FatalRunError) as e:
        print(f"\nERROR: {e}")
        return 1

    if not result.runs:
        print("\nERROR: no run produced usable data.")
        for failure in result.failures:
            print(f"  {failure}")
        return 1
    if result.failures:
        print(f"\nWARNING: {len(result.failures)} run(s) failed, reports use {len(result.runs)} run(s).")

    print("----------------------- START CALC & CREATE OUTPUT STAGE ----------------------- ")
    Path(params.output_path).mkdir(parents=True, exist_ok=True)
    meta = report_meta(result, platform)
    averages = calculate_averages(result.entries)
    save_csv_with_data(averages, params, meta)
    save_png_with_data(averages, params, meta)
    print(f"\nDone. CSV: {params.csv_path}\n      PNG: {params.png_path}")
    return 0


def measure(params):
    print("\n----------------------- VALIDATION STEP ----------------------- ")
    platform = create_platform(params)
    print("----------------------- VALIDATION PASSED -> PREPARE STAGE----------------------- ")
    try:
        platform.prepare()
        print("----------------------- PREPARE STAGE PASSED -> MEASUREMENT STAGE ----------------------- ")
        result = start_measurements(platform, params)
        print(f"----------------------- MEASUREMENT STAGE DONE: {len(result.runs)}/{params.launch_times} "
              "runs usable -----------------------")
        if platform.note():
            print(f"NOTE: {platform.note()}")
        return result, platform
    finally:
        platform.cleanup()


if __name__ == '__main__':
    sys.exit(main())


########## PREPARE #########
# cd [root of RN project]
# python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
# Only adb (Android) and Xcode command line tools (iOS) are needed on the host.

########## LAUNCH #########
# python3 main.py --platform android --launch_times 10
