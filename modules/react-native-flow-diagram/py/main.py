from device_utils import validate_device_and_package, prevent_screen_lock, close_app, compile_package
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
    print("----------------------- VALIDATION PASSED -> START PREPARE STAGE----------------------- ")


    # Prepare
    prevent_screen_lock(True)
    close_app()
    compile_package()
    print("----------------------- PREPARE STAGE PASSED -> START MEASUREMENT STAGE ----------------------- ")

    # Launch and measure
    all_android_data, all_ios_data = start_measurements()

    print("----------------------- MEASUREMENT STAGE PASSED -> START CLEAN STAGE ----------------------- ")

    # Clean
    prevent_screen_lock(False)
    close_app()

    print("----------------------- CLEAN STAGE PASSED -> START CALC & CREATE OUTPUT STAGE ----------------------- ")


    create_folders()

    # Calculate
    if all_android_data:
        averages_android = calculate_averages(all_android_data)
        # Save and show results
        save_csv_with_data(averages_android)
        save_png_with_data(averages_android)

    if all_ios_data:
        averages_ios = calculate_averages(all_ios_data)
        # Save and show results
        save_csv_with_data(averages_ios)
        save_png_with_data(averages_ios)


