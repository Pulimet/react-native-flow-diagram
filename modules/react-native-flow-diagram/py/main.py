from ad_device_utils import validate_device_and_package, prevent_screen_lock, close_app, compile_package
from measurements import start_measurements
from calc_average import calculate_averages
from utils import create_folders
from csv_utils import save_csv_with_data
from visualize import save_png_with_data

if __name__ == "__main__":
    print("Measurement script launched...")
    is_android_passed, is_ios_passed = validate_device_and_package()

    # Exit if no platform is validated successfully
    if not is_android_passed and not is_ios_passed:
        print("Validation failed for all enabled platforms. Exiting.")
        exit(1)


    # Prepare
    prevent_screen_lock(True)
    close_app()
    compile_package()

    # Launch and measure
    all_data = start_measurements()

    # Clean
    prevent_screen_lock(False)
    close_app()

    # Calculate
    averages = calculate_averages(all_data)

    # Save and show results
    create_folders()
    save_csv_with_data(averages)
    save_png_with_data(averages)
