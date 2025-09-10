import time
import ios_device_utils

from config import LAUNCH_COUNT, WAIT_TIME, ANDROID_LOG_TAG, IOS_LOG_EMU_TAG, IOS_LOG_REAL_TAG
from device_utils import close_app, launch_app, clear_logs, capture_logs_android, start_capturing_ios_logs, stop_capturing_ios_logs
from parsing_utils import parse_logs

def start_measurements():
    print(f"Launching and collecting data {LAUNCH_COUNT} times...")
    all_android_data_list = []
    all_ios_data_list = []
    for i, _ in enumerate(range(LAUNCH_COUNT)):
        print(f"Iteration {i + 1}/{LAUNCH_COUNT}")
        data_android, data_ios = launch_and_collect_data()
        if data_android:
            all_android_data_list.extend(data_android)
        if data_ios:
            all_ios_data_list.extend(data_ios)
    return all_android_data_list, all_ios_data_list


def launch_and_collect_data():
    close_app()
    clear_logs()

    #iOS
    start_capturing_ios_logs()

    launch_app()

    # Python script wait for X seconds
    print(f"Waiting for {WAIT_TIME} seconds...")
    time.sleep(WAIT_TIME)

    #IOS
    ios_logs = stop_capturing_ios_logs()
    parsed_ios_logs = None
    if ios_logs:
        log_tag = IOS_LOG_EMU_TAG
        if ios_device_utils.is_real_ios_device_target:
            log_tag = IOS_LOG_REAL_TAG
        parsed_ios_logs = parse_logs(ios_logs, log_tag)

    # Android
    android_logs = capture_logs_android()
    parsed_android_logs = None
    if android_logs:
        parsed_android_logs = parse_logs(android_logs, ANDROID_LOG_TAG)

    return parsed_android_logs, parsed_ios_logs
