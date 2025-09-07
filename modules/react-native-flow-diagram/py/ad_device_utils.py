import subprocess

from config import PACKAGE, ACTIVITY, EXTRA_KEY, EXTRA_VALUE, IS_ANDROID_ENABLED, IS_IOS_ENABLED

REQUIRED_DEVICES = 1
# Screen timeout 5 minutes as a string
TIMEOUT_5 = "300000"
# Screen timeout  60 minutes as a string
TIMEOUT_60 = "3600000"

def validate_device_and_package():
    is_android_passed = IS_ANDROID_ENABLED and validate_android()
    is_ios_passed = IS_IOS_ENABLED and validate_ios()
    return is_android_passed, is_ios_passed

def validate_ios():
    return False


def validate_android():
    # Check if the required number of devices is connected
    devices = subprocess.check_output(["adb", "devices"]).decode("utf-8").splitlines()
    devices_found = len(devices) - 2  #-2 for the header and trailing empty line

    if devices_found != REQUIRED_DEVICES:
        device_str = "device" if REQUIRED_DEVICES == 1 else "devices"
        print(f"Validation of Android device failed: Expected {REQUIRED_DEVICES} connected {device_str}, but found {devices_found}.")
        print("Run 'adb devices' in your terminal to see the list of connected devices.")
        return False

    # Check if the required package is installed
    package_info = subprocess.check_output(["adb", "shell", "pm", "list", "packages"]).decode("utf-8").splitlines()
    if f"package:{PACKAGE}" not in package_info:
        print(f"Validation failed: The package '{PACKAGE}' is not installed.")
        return False

    print("Validation passed: Device connected and package installed.")
    return True


def prevent_screen_lock(enable=True):
    if enable:
        print("Preventing the device screen from locking...")
    else:
        print("Allowing the device screen to lock...")

    command = ["adb", "shell", "settings", "put", "system", "screen_off_timeout",
               TIMEOUT_60 if enable else TIMEOUT_5]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def close_app():
    print("Closing the app if it was running...")
    subprocess.run(["adb", "shell", "am", "force-stop", PACKAGE])

def compile_package():
    print("Compiling the package...")
    subprocess.run(["adb", "shell", "cmd", "package", "compile", "-m", "speed", "-f", PACKAGE])

def launch_app():
    print("Launching the app...")
    subprocess.run(
        ["adb", "shell", "monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def launch_activity_with_extras():
    print(f"Launching {ACTIVITY} with specific intent...")
    command = [
        "adb", "shell", "am", "start",
        "-n", f"{PACKAGE}/{ACTIVITY}",
        "-a", "android.intent.action.VIEW",
        "-c", "android.intent.category.DEFAULT",
        "--ez", f"{EXTRA_KEY}", f"{EXTRA_VALUE}"
    ]
    print(command)
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
