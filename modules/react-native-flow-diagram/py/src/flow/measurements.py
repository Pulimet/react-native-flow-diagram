import time
from device.device_utils import close_app, launch_app, clear_logs, capture_logs_android, start_capturing_ios_logs, stop_capturing_ios_logs
from parsing_utils import parse_logs

ANDROID_LOG_TAG = "FlowDiagramTime"
IOS_LOG_EMU_TAG = "FlowDiagram:FlowDiagram"
IOS_LOG_REAL_TAG = " <Error>"

def start_measurements(platform, wait_time, package, bundle_id, extra, activity, extra_key, extra_value, launch_times):
    print(f"Launching and collecting data {launch_times} times...")
    data = []
    for i, _ in enumerate(range(launch_times)):
        print(f"Iteration {i + 1}/{launch_times}")
        data_result = launch_and_collect_data(platform, wait_time, package, bundle_id, extra, activity, extra_key, extra_value)
        data.extend(data_result)
    return data


def launch_and_collect_data(platform, wait_time, package, bundle_id, extra, activity, extra_key, extra_value):
    close_app(platform, package, bundle_id)
    clear_logs(platform) # only Android
    start_capturing_ios_logs(platform, bundle_id) # only iOS
    launch_app(platform, bundle_id, package, extra, activity, extra_key, extra_value)

    # Python script wait for X seconds
    print(f"Waiting for {wait_time} seconds...")
    time.sleep(wait_time)

    parsed_logs = None

    if platform == 'android':
        logs = capture_logs_android(platform, wait_time, ANDROID_LOG_TAG)
        if logs:
            parsed_logs = parse_logs(logs, ANDROID_LOG_TAG)
    else:
        logs = stop_capturing_ios_logs(platform)
        log_tag = platform == 'ios_simulator' and IOS_LOG_EMU_TAG or IOS_LOG_REAL_TAG
        if logs:
            parsed_logs = parse_logs(logs, log_tag)

    return parsed_logs
