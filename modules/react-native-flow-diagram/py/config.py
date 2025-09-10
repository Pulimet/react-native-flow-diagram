from datetime import datetime

########## PREPARE #########
# Below used to receive iOS logs from real device
# brew install libimobiledevice

# cd [root of RN project]
# python3 -m venv .venv
# source .venv/bin/activate
# pip install matplotlib --timeout 1000 --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org

########## LAUNCH #########
# python3 main.py

# Global Config
IS_ANDROID_ENABLED = False
IS_IOS_ENABLED = True
IS_FORCE_EMULATOR = False

# App config
# You can find this in Xcode under Target > General > Identity > Bundle Identifier.
BUNDLE_ID = "org.reactjs.native.example.FlowDiagram" # iOS
PACKAGE = "com.flowdiagram" # Android
ANDROID_LOG_TAG = "FlowDiagramTime"

#iOS config
IOS_LOG_EMU_TAG = "FlowDiagram:FlowDiagram"
IOS_LOG_REAL_TAG = " <Error>"

# Android Launch Config
EXTRA_ANDROID_ENABLED = False # Used when FlowDiagram is disabled by default and app should be launched with special extra
ACTIVITY = "com.flowdiagram.MainActivity"
EXTRA_KEY = "time"
EXTRA_VALUE = "true"

# Measurements Config
LAUNCH_COUNT = 1
WAIT_TIME = 8
WAIT_LOGS = 1

# Parsing Config
SHOW_NETWORK_REQUEST = True
SHOW_NETWORK_RESPONSE = True
SHOW_REGULAR_LOG = True
FILTER_NETWORK_REQUEST = ""

# Output Folder Config
OUTPUT_DIR = "output"
DATE = datetime.now().strftime('%y-%m-%d')
OUTPUT_PATH = f"{OUTPUT_DIR}/{DATE}"

# Output File Config
FILE_NAME_PREFIX = "measure"
DATE_TIME = datetime.now().strftime('%y-%m-%d_%H-%M')
FILE_NAME = f"{FILE_NAME_PREFIX}_{DATE_TIME}"
FILE_PATH = f"{OUTPUT_PATH}/{FILE_NAME}"

# Diagram Config
VISUAL_URL = 160
VISUAL_ADD_TIME_AT_THE_END = 8000
PNG_PATH = f"{FILE_PATH}.png"

# Action After Complete
OPEN_CSV = False
OPEN_PNG = False



