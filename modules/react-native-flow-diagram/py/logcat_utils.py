import subprocess
from config import LOG_TAG

def capture_logcat_output(timeout):
    print(f"Capturing logcat output with timeout of {timeout} seconds...")
    logcat_process = subprocess.Popen(
        ["adb", "logcat", f"{LOG_TAG}:I *:S"],
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

def clear_logcat():
    print("Clearing logcat...")
    subprocess.run(["adb", "logcat", "-c"])
