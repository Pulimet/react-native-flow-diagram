import time
from device.device_utils import close_app, launch_app, clear_logs, capture_logs_android, start_capturing_ios_logs, stop_capturing_ios_logs
from parsing_utils import parse_logs

ANDROID_LOG_TAG = "FlowDiagramTime"
IOS_LOG_EMU_TAG = "FlowDiagram:FlowDiagram"
IOS_LOG_REAL_TAG = " <Error>"

def start_measurements(params):
    print(f"Launching and collecting data {params.launch_times} times...")
    data = []
    for i, _ in enumerate(range(params.launch_times)):
        print(f"Iteration {i + 1}/{params.launch_times}")
        data_result = launch_and_collect_data(params)
        data.extend(data_result)
    return data


def launch_and_collect_data(params):
    close_app(params)
    clear_logs(params.platform) # only Android
    start_capturing_ios_logs(params) # only iOS
    launch_app(params)

    # Python script wait for X seconds
    print(f"Waiting for {params.wait_time} seconds...")
    time.sleep(params.wait_time)

    parsed_logs = None

    if params.platform == 'android':
        logs = capture_logs_android(params, ANDROID_LOG_TAG)
        if logs:
            parsed_logs = parse_logs(logs, ANDROID_LOG_TAG)
    else:
        logs = stop_capturing_ios_logs(params.platform)
        log_tag = params.platform == 'ios_simulator' and IOS_LOG_EMU_TAG or IOS_LOG_REAL_TAG
        if logs:
            parsed_logs = parse_logs(logs, log_tag)

    return parsed_logs
