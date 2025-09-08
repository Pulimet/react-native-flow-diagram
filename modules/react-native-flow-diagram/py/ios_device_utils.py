import subprocess
import re
import os

from config import BUNDLE_ID

REQUIRED_DEVICES = 1

# Module-level variables to store the validation state.
# They are accessible by any function within this file after being set.
_real_device_count = 0
_booted_sim_count = 0
_is_simulator_target = False
_is_real_device_target = False

def validate_ios():
    """Validates that exactly one iOS device or simulator is ready."""
    try:
        global _real_device_count, _booted_sim_count, _is_simulator_target, _is_real_device_target
        _real_device_count = _get_real_device_count()
        _booted_sim_count = _get_booted_simulator_count()
        _is_simulator_target = (_booted_sim_count == 1 and _real_device_count == 0)
        _is_real_device_target = (_real_device_count == 1 and _booted_sim_count == 0)

        print(f"real_device_count: {_real_device_count}")
        print(f"booted_sim_count: {_booted_sim_count}")

        total_targets = _real_device_count + _booted_sim_count
        if total_targets == REQUIRED_DEVICES:
            print(f"Validation passed: Found {total_targets} iOS target (device/simulator).")
            return True
        else:
            print(f"Validation of iOS device/simulator failed: Expected {REQUIRED_DEVICES} target, but found {total_targets}.")
            return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Validation of iOS failed: `xcrun` command-line tools not found or failed. Make sure Xcode is installed.")
        return False

def _get_real_device_count():
    """Counts connected physical iOS devices using xcrun."""
    real_devices_output = subprocess.check_output(["xcrun", "xctrace", "list", "devices"], text=True, stderr=subprocess.PIPE)
    lines = real_devices_output.splitlines()
    device_section = False
    real_device_count = 0
    for line in lines:
        # If we hit any new section header, we are no longer in the active "Devices" section.
        if line.strip().startswith("==") and not line.strip() == "== Devices ==":
            device_section = False
        if line.startswith("== Devices =="):
            device_section = True
            continue # Skip the header line itself

        # A real, connected device has an OS version like (18.6.2) in its line.
        # This check only runs when device_section is True.
        if device_section and re.search(r'\([\d.]+\)', line):
            real_device_count += 1
    return real_device_count

def _get_booted_simulator_count():
    """Counts booted iOS simulators using xcrun."""
    simulators_output = subprocess.check_output(["xcrun", "simctl", "list", "devices"], text=True)
    lines = simulators_output.splitlines()
    booted_sim_count = 0
    # Regex to find an iOS runtime section header, e.g., "-- iOS 17.2 --"
    ios_section_regex = re.compile(r"^-- iOS [\d.]+ --$")
    in_ios_section = False
    for line in lines:
        if ios_section_regex.match(line.strip()):
            in_ios_section = True
        elif in_ios_section and line.strip().startswith("--"): # A new OS section starts, exit iOS section
            in_ios_section = False
        if in_ios_section and '(Booted)' in line:
            booted_sim_count += 1
    return booted_sim_count

def prevent_ios_screen_lock(enable=True):
    """
    Prevents the screen from locking on a booted iOS simulator.
    This functionality is not supported for physical devices via command line.
    """
    try:
        if _is_simulator_target:
            action_str = "Disabling" if enable else "Enabling"
            print(f"{action_str} screen auto-lock on the iOS simulator...")

            # We must modify the simulator's plist file directly on the host machine.
            # First, get the UDID of the booted simulator.
            udid = _get_booted_simulator_udid()
            if not udid:
                print("ERROR: Could not find the UDID of the booted simulator.")
                return

            # Construct the path to the springboard preferences file.
            plist_path = os.path.expanduser(f"~/Library/Developer/CoreSimulator/Devices/{udid}/data/Library/Preferences/com.apple.springboard.plist")

            # Ensure the directory for the plist file exists, as it might not on a fresh simulator.
            os.makedirs(os.path.dirname(plist_path), exist_ok=True)

            command = [
                "defaults", "write", f"{plist_path}",
                "SBIdleTimerDisabled", "-bool", "true" if enable else "false"
            ]
            subprocess.run(command, check=True, capture_output=True)

            # --- Validation Step ---
            # Read the setting back to verify the change.
            try:
                read_command = ["defaults", "read", plist_path, "SBIdleTimerDisabled"]
                result = subprocess.check_output(read_command, text=True, stderr=subprocess.PIPE).strip()
                expected_value = "1" if enable else "0"

                if result == expected_value:
                    print("Successfully verified screen lock setting change.")
                else:
                    print(f"ERROR: Verification of screen lock setting failed. Expected '{expected_value}' but found '{result}'.")
                    return
            except subprocess.CalledProcessError:
                print("ERROR: Could not read back screen lock setting to verify the change.")
                return

            # Restart the springboard to apply the change
            # The most reliable way is to use `simctl terminate` with the SpringBoard bundle ID.
            print("Restarting simulator's SpringBoard to apply settings...")
            springboard_bundle_id = "com.apple.springboard"
            # We remove `check=True` because this command may fail if SpringBoard restarts automatically
            # after the `defaults write` command. In that case, failing is the desired outcome.
            subprocess.run(["xcrun", "simctl", "terminate", "booted", springboard_bundle_id],
                           capture_output=True)

        elif _is_real_device_target:
            print("INFO: Screen lock settings cannot be changed on physical iOS devices via the command line due to security restrictions.")

        elif _booted_sim_count + _real_device_count > 1:
            print("INFO: Multiple simulators/devices are running. Screen lock setting was not changed.")

        else:
            print("INFO: No single iOS simulator or device found to apply screen lock settings.")

    except subprocess.CalledProcessError as e:
        print("ERROR: A command failed while trying to change screen lock settings.")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"Stderr: {e.stderr.decode('utf-8').strip()}")
    except FileNotFoundError as e:
        print(f"ERROR: Command not found: {e.filename}. Ensure Xcode command-line tools are installed.")

def _get_booted_simulator_udid():
    """Gets the UDID of the single booted iOS simulator."""
    simulators_output = subprocess.check_output(["xcrun", "simctl", "list", "devices"], text=True)
    lines = simulators_output.splitlines()
    ios_section_regex = re.compile(r"^-- iOS [\d.]+ --$")
    in_ios_section = False
    for line in lines:
        if ios_section_regex.match(line.strip()):
            in_ios_section = True
        elif in_ios_section and line.strip().startswith("--"):
            in_ios_section = False

        if in_ios_section and '(Booted)' in line:
            # Extract the UDID from a line like: "iPhone 15 Pro (UDID) (Booted)"
            match = re.search(r'([A-F0-9]{8}-(?:[A-F0-9]{4}-){3}[A-F0-9]{12})', line)
            if match:
                return match.group(1)
    return None

def close_ios_app():
    """Closes the app on the connected iOS device or booted simulator."""
    print(f"Closing app with bundle ID: {BUNDLE_ID}...")

    try:
        if _is_simulator_target:
            # For a simulator, 'booted' is a convenient target.
            command = ["xcrun", "simctl", "terminate", "booted", BUNDLE_ID]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                print("Successfully sent terminate signal to the app on the simulator.")
            else:
                # simctl terminate exits with a non-zero code if the app wasn't running, which is fine.
                print("App was not running on the simulator or could not be terminated.")

        elif _is_real_device_target:
            print("INFO: Closing apps on physical devices is not supported by this script due to command-line limitations.")
            print("Please close the app manually on the device.")

        elif _get_booted_simulator_count() > 1 or _get_real_device_count() > 1:
            print("INFO: Multiple devices/simulators found. No action taken.")

        else:
            print("INFO: No single iOS simulator or device found. No action taken.")

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print("ERROR: A command failed while trying to close the app.")
        if isinstance(e, FileNotFoundError):
            print(f"Command not found: {e.filename}. Ensure Xcode command-line tools are installed.")

def clear_ios_logs():
    print("TODO: clear_ios_logs")

def launch_ios_app():
    """Launches the app on the booted simulator."""
    print(f"Launching app with bundle ID: {BUNDLE_ID}...")

    try:
        if _is_simulator_target:
            command = ["xcrun", "simctl", "launch", "booted", BUNDLE_ID]
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"Successfully launched app with bundle ID: {BUNDLE_ID} on the simulator.")

        elif _is_real_device_target:
            print("INFO: Launching apps on physical devices is not supported by this script.")
            print("Please launch the app manually on the device.")

        elif _get_booted_simulator_count() > 1 or _get_real_device_count() > 1:
            print("INFO: Multiple devices/simulators found. No action taken.")

        else:
            print("INFO: No single iOS simulator or device found. No action taken.")

    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to launch app with bundle ID: {BUNDLE_ID}")
        print(f"Stderr: {e.stderr.strip()}")
    except FileNotFoundError:
        print("ERROR: `xcrun` command not found. Make sure Xcode command-line tools are installed.")
