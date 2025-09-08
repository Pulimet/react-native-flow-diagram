import subprocess
from config import ANDROID_LOG_TAG

def capture_android_logs(timeout):
    print(f"Capturing logcat output with timeout of {timeout} seconds...")
    logcat_process = subprocess.Popen(
        ["adb", "logcat", f"{ANDROID_LOG_TAG}:I *:S"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    try:
        stdout, stderr = logcat_process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        logcat_process.kill()
        stdout, stderr = logcat_process.communicate()

    if stderr:
        print("Error during logcat capture:")
        print(stderr)

    return stdout.splitlines()

def clear_android_logs():
    print("Clearing logcat...")
    subprocess.run(["adb", "logcat", "-c"])
