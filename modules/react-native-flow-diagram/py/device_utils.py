from config import IS_ANDROID_ENABLED, IS_IOS_ENABLED, EXTRA_ANDROID_ENABLED
from ad_device_utils import validate_android, prevent_android_screen_lock, close_android_app, compile_android_package, launch_android_app, launch_activity_with_extras
from ios_device_utils import validate_ios, prevent_ios_screen_lock, close_ios_app, launch_ios_app, clear_ios_logs
from logcat_utils import clear_android_logs

# Module-level variables to store the validation state.
# They are accessible by any function within this file after being set.
_is_android_validated = False
_is_ios_validated = False

def validate_device_and_package():
    global _is_android_validated, _is_ios_validated
    _is_android_validated = IS_ANDROID_ENABLED and validate_android()
    _is_ios_validated = IS_IOS_ENABLED and validate_ios()
    return _is_android_validated, _is_ios_validated

def prevent_screen_lock(enable=True):
    if _is_android_validated:
        prevent_android_screen_lock(enable)

    if _is_ios_validated:
        prevent_ios_screen_lock(enable)

def close_app():
    if _is_android_validated:
        close_android_app()

    if _is_ios_validated:
        close_ios_app()

def compile_package():
    if _is_android_validated:
        compile_android_package()

def clear_logs():
    if _is_android_validated:
        clear_android_logs()

    if _is_ios_validated:
        clear_ios_logs()

def launch_app():
    if _is_android_validated:
        if EXTRA_ANDROID_ENABLED:
            launch_activity_with_extras()
        else:
             launch_android_app()

    if _is_ios_validated:
        launch_ios_app()


