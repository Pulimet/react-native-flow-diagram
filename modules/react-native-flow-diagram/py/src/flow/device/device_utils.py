from .ad_device_utils import validate_android, prevent_android_screen_lock, close_android_app, compile_android_package, launch_android_app, launch_activity_with_extras
from .ios_device_utils import validate_ios_simulator, validate_ios_device, prevent_ios_screen_lock, close_ios_device_app,  close_ios_simulator_app, start_ios_log_capture, stop_ios_log_capture, launch_ios_device_app, launch_ios_simulator_app
from .logcat_utils import clear_android_logs, capture_android_logs

def validate_device_and_package(platform, package):
    status = False
    if platform == 'android':
        status = validate_android(package)
    if platform == 'ios_device':
        status = validate_ios_device()
    if platform == 'ios_simulator':
        status = validate_ios_simulator()
    return status

def prevent_screen_lock(enable, platform):
    if platform == 'android':
        prevent_android_screen_lock(enable)
    if platform == 'ios_simulator':
        prevent_ios_screen_lock(enable)
    if platform == 'ios_device':
        print("Screen lock prevention is not supported on iOS devices.")

def close_app(platform, package, bundle_id):
    if platform == 'android':
        close_android_app(package)
    if platform == 'ios_simulator':
        close_ios_simulator_app(bundle_id)
    if platform == 'ios_device':
        close_ios_device_app(bundle_id)

def compile_package(platform, package):
    if platform == 'android':
        compile_android_package(package)

def clear_logs(platform):
    if platform == 'android':
        clear_android_logs()

def launch_app(platform, bundle_id, package, activity, extra, extra_key, extra_value):
    if platform == 'android':
        if extra:
            launch_activity_with_extras(package, activity, extra_key, extra_value)
        else:
             launch_android_app(package)
    if platform == 'ios_simulator':
        launch_ios_simulator_app(bundle_id)
    if platform == 'ios_device':
        launch_ios_device_app(bundle_id)


def capture_logs_android(platform, wait_time, ad_log_tag):
    android_logs = None
    if platform == 'android':
        android_logs = capture_android_logs(wait_time, ad_log_tag)

    return android_logs

def start_capturing_ios_logs(platform, bundle_id):
    if platform != 'android':
        start_ios_log_capture(platform, bundle_id)

def stop_capturing_ios_logs(platform):
    if platform != 'android':
        return stop_ios_log_capture()
    return None
