import subprocess
from config import OUTPUT_DIR, OUTPUT_PATH

def create_folders():
    print(f"Creating folder {OUTPUT_DIR}...")
    # Create local (mac) folder if not exist:
    subprocess.run(["mkdir", "-p", OUTPUT_DIR])
    subprocess.run(["mkdir", "-p", OUTPUT_PATH])
