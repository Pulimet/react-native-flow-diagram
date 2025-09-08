import time

from config import LAUNCH_COUNT, WAIT_TIME, WAIT_LOGS, EXTRA_ENABLED
from device_utils import close_app
from ad_device_utils import launch_app, launch_activity_with_extras
from logcat_utils import capture_android_logs, clear_android_logs
from parsing_utils import parse_data

def start_measurements():
    print(f"Launching and collecting data {LAUNCH_COUNT} times...")
    all_data_list = []
    for i, _ in enumerate(range(LAUNCH_COUNT)):
        print(f"Iteration {i + 1}/{LAUNCH_COUNT}")
        data = launch_and_collect_data()
        all_data_list.extend(data)
    return all_data_list

def launch_and_collect_data():
    close_app()
    clear_android_logs()
    if EXTRA_ENABLED:
        launch_activity_with_extras()
    else:
        launch_app()

    # Python script wait for X seconds
    print(f"Waiting for {WAIT_TIME} seconds...")
    time.sleep(WAIT_TIME)

    logcat_output = capture_android_logs(WAIT_LOGS)

    return parse_data(logcat_output)
