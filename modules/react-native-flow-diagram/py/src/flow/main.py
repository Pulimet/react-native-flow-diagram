import subprocess

from cli.cli_args import parse_args
from device.device_utils import validate_device_and_package, prevent_screen_lock, close_app, compile_package
from measurements import start_measurements
from calc_average import calculate_averages
from csv_utils import save_csv_with_data
from visualize import save_png_with_data

def main():
    print("----------------------- Measurement Script Started----------------------- ")
    platform, package, extra, bundle_id, wait_time, activity, extra_key, extra_value, launch_times, csv_path, csv_net_path, png_path, output_dir, output_path, open_csv, open_png  = parse_args()
    print("\n----------------------- VALIDATION STEP ----------------------- ")

    if not validate_device_and_package(platform, package):
        print("\nValidation step failed.")
        exit(1) # Exit if no platform is validated successfully
    print("----------------------- VALIDATION PASSED -> PREPARE STAGE----------------------- ")

    # Prepare
    prevent_screen_lock(True, platform)
    close_app(platform, package, bundle_id)
    compile_package(platform, package)
    print("----------------------- PREPARE STAGE PASSED -> MEASUREMENT STAGE ----------------------- ")

    # Launch and measure
    data = start_measurements(platform, wait_time, package, bundle_id, extra, activity, extra_key, extra_value, launch_times)

    print("----------------------- MEASUREMENT STAGE PASSED -> START CLEAN STAGE ----------------------- ")

    # Clean
    prevent_screen_lock(False, platform)
    close_app(platform, package, bundle_id)

    print("----------------------- CLEAN STAGE PASSED -> START CALC & CREATE OUTPUT STAGE ----------------------- ")
    create_folders(output_dir, output_path)
    # Calculate
    averages = calculate_averages(data)
    # Save and show results
    report_package = package if platform == 'android' else bundle_id
    save_csv_with_data(averages, report_package, launch_times, wait_time, csv_path, csv_net_path, open_csv)
    save_png_with_data(averages, png_path, open_png)

def create_folders(output_dir, output_path):
    print(f"Creating folder {output_dir}...")
    # Create local (mac) folder if not exist:
    subprocess.run(["mkdir", "-p", output_dir])
    subprocess.run(["mkdir", "-p", output_path])

if __name__ == '__main__':
    main()



########## PREPARE #########
# Below used to receive iOS logs from real device
# brew install libimobiledevice

# cd [root of RN project]

# Create a virtual environment
# python3 -m venv .venv

# Activate the virtual environment (Mac/Linux)
# source .venv/bin/activate

# poetry install

# pip install matplotlib --timeout 1000 --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
# pip install poetry-core --timeout 1000 --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org

########## LAUNCH #########
# python3 main.py