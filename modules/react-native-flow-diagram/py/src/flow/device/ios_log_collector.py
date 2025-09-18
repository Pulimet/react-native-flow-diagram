import subprocess
import fcntl
import os

class IOSLogCollector:
    """
    Manages an asynchronous log capture process for an iOS device or simulator.
    """
    def __init__(self):
        self._log_process = None
        self._is_simulator = False
        self._is_real_device = False

    def start(self, platform, bundle_id):
        """Starts capturing logs in a background subprocess."""
        self._is_simulator = platform == 'ios_simulator'
        self._is_real_device = platform == 'ios_device'

        if self._log_process:
            print("INFO: Log capture is already running.")
            return

        if not self._is_simulator and not self._is_real_device:
            print("INFO: No single iOS simulator or device found. Cannot capture logs.")
            return

        predicate = f'subsystem == "{bundle_id}"'

        if self._is_simulator:
            command = [
                "xcrun", "simctl", "spawn", "booted", "log", "stream",
                "--debug", "--predicate", predicate
            ]
        else:  # is_real_device
            # xcrun log stream --level info --style default --predicate 'process == "FlowDiagram'
            # idevicesyslog -m "FlowDiagram(FlowDiagram.debug"
            command = ["idevicesyslog", "-m", "FlowDiagram.debug.dylib"]


        print("Starting iOS log capture...")
        print(f">>> Executing command: {' '.join(command)}")

        self._log_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors='replace'
        )
        # Make pipes non-blocking
        fcntl.fcntl(self._log_process.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
        fcntl.fcntl(self._log_process.stderr, fcntl.F_SETFL, os.O_NONBLOCK)

    def stop(self):
        """Stops the log capture process and returns the collected logs."""
        if not self._log_process:
            print("INFO: Log capture was not running.")
            return []

        print("Stopping iOS log capture...")
        # Try to terminate gracefully first, then kill
        self._log_process.terminate()
        try:
            # Wait a very short moment to see if it terminates on its own
            self._log_process.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            # Force kill if it's still running
            self._log_process.kill()

        # Read remaining output from non-blocking pipes
        stdout = ""
        stderr = ""
        while True:
            try:
                stdout_chunk = self._log_process.stdout.read()
                stderr_chunk = self._log_process.stderr.read()
                if not stdout_chunk and not stderr_chunk:
                    break
                stdout += stdout_chunk if stdout_chunk else ""
                stderr += stderr_chunk if stderr_chunk else ""
            except (IOError, TypeError): # In Python 3.5+, read() on a closed pipe may raise TypeError
                break

        self._log_process = None  # Reset for next use

        if stderr:
            # Filter out common non-error messages from stderr
            if "xcrun: error" in stderr.lower() or "invalid predicate" in stderr.lower():
                print("--- iOS Log Capture STDERR ---")
                print(stderr.strip())
                print("-----------------------------")

        if not stdout.strip():
            print("\n--- No iOS logs were captured. ---")
            print("-----------------------------------\n")
            return []

        print("\n--- iOS Log Capture STDOUT ---")
        print(stdout.strip())
        print("-----------------------------")
        return stdout.splitlines()
