import subprocess

from cli.cli_args import parse_args
from device.device_utils import validate_device_and_package, prevent_screen_lock, close_app, compile_package
from measurements import start_measurements
from calc_average import calculate_averages
from csv_utils import save_csv_with_data
from visualize import save_png_with_data

def main():
    print("----------------------- Measurement Script Started----------------------- ")
    params  = parse_args()
    print("\n----------------------- VALIDATION STEP ----------------------- ")

    if not validate_device_and_package(params):
        print("\nValidation step failed.")
        exit(1) # Exit if no platform is validated successfully
    print("----------------------- VALIDATION PASSED -> PREPARE STAGE----------------------- ")

    # Prepare
    prevent_screen_lock(True, params.platform)
    close_app(params)
    compile_package(params)
    print("----------------------- PREPARE STAGE PASSED -> MEASUREMENT STAGE ----------------------- ")

    # Launch and measure
    data = start_measurements(params)

    print("----------------------- MEASUREMENT STAGE PASSED -> START CLEAN STAGE ----------------------- ")

    # Clean
    prevent_screen_lock(False, params.platform)
    close_app(params)

    print("----------------------- CLEAN STAGE PASSED -> START CALC & CREATE OUTPUT STAGE ----------------------- ")
    create_folders(params)
    # Calculate
    averages = calculate_averages(data)
    # Save and show results
    save_csv_with_data(averages, params)
    save_png_with_data(averages, params)

def create_folders(params):
    print(f"Creating folder {params.output_dir}...")
    # Create local (mac) folder if not exist:
    subprocess.run(["mkdir", "-p", params.output_dir])
    subprocess.run(["mkdir", "-p", params.output_path])

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