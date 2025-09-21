from .ad_device_utils import validate_android, prevent_android_screen_lock, close_android_app, compile_android_package, launch_android_app, launch_activity_with_extras
from .ios_device_utils import validate_ios_simulator, validate_ios_device, prevent_ios_screen_lock, close_ios_device_app,  close_ios_simulator_app, start_ios_log_capture, stop_ios_log_capture, launch_ios_device_app, launch_ios_simulator_app
from .logcat_utils import clear_android_logs, capture_android_logs

def validate_device_and_package(params):
    status = False
    if params.platform == 'android':
        status = validate_android(params.package)
    if params.platform == 'ios_device':
        status = validate_ios_device()
    if params.platform == 'ios_simulator':
        status = validate_ios_simulator()
    return status

def prevent_screen_lock(enable, platform):
    if platform == 'android':
        prevent_android_screen_lock(enable)
    if platform == 'ios_simulator':
        prevent_ios_screen_lock(enable)
    if platform == 'ios_device':
        print("Screen lock prevention is not supported on iOS devices.")

def close_app(params):
    if params.platform == 'android':
        close_android_app(params.package)
    if params.platform == 'ios_simulator':
        close_ios_simulator_app(params.bundle_id)
    if params.platform == 'ios_device':
        close_ios_device_app(params.bundle_id)

def compile_package(params):
    if params.platform == 'android':
        compile_android_package(params.package)

def clear_logs(platform):
    if platform == 'android':
        clear_android_logs()

def launch_app(params):
    if params.platform == 'android':
        if params.extra:
            launch_activity_with_extras(params)
        else:
             launch_android_app(params.package)
    if params.platform == 'ios_simulator':
        launch_ios_simulator_app(params)
    if params.platform == 'ios_device':
        launch_ios_device_app(params)


def capture_logs_android(params, ad_log_tag):
    android_logs = None
    if params.platform == 'android':
        android_logs = capture_android_logs(params.wait_time, ad_log_tag)

    return android_logs

def start_capturing_ios_logs(params):
    if params.platform != 'android':
        start_ios_log_capture(params.platform, params.bundle_id)

def stop_capturing_ios_logs(platform):
    if platform != 'android':
        return stop_ios_log_capture()
    return None
