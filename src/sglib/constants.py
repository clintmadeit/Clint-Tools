import os
import pathlib
import platform
import sys

__all__ = [
    'CONFIG_DIR',
    'DEFAULT_PROJECT_DIR',
    'HOME',
    'IS_LINUX',
    'IS_MACOS',
    'IS_WINDOWS',
    'LOG_DIR',
    'MAJOR_VERSION',
    'PRESET_DIR',
    'USER_HOME',
]

MAJOR_VERSION = 'stargate'

MIDI_CHANNELS = [str(x) for x in range(1, 17)] + ['All']

ARCH = platform.machine()
assert "cygwin" not in sys.platform, "Cygwin is unsupported"
IS_WINDOWS = "win32" in sys.platform or "msys" in sys.platform
IS_LINUX = "linux" in sys.platform
IS_MACOS = "darwin" in sys.platform

USER_HOME = os.path.expanduser("~")
IS_PORTABLE_INSTALL = False
PORTABLE_ROOT = None

# Check if the exe was run from a flash drive, with a '_stargate_home' file
# created in the same directory
if IS_WINDOWS:
    dirname = os.path.dirname(sys.executable)
    if os.path.isfile(
        os.path.join(dirname, '..', '_stargate_home'),
    ):
        USER_HOME = os.path.abspath(
            os.path.join(dirname, '..'),
        )
        print(
            f"Using {USER_HOME} for USER_HOME because _stargate_home "
            "file exists"
        )
        IS_PORTABLE_INSTALL = True
        PORTABLE_ROOT = pathlib.Path(sys.executable).drive.upper()
elif IS_MACOS:
    dirname = os.path.dirname(sys.executable)
    if os.path.isfile(
        os.path.join(dirname, '..', '..', '..', '_stargate_home'),
    ):
        USER_HOME = os.path.abspath(
            os.path.join(dirname, '..', '..', '..'),
        )
        print(
            f"Using {USER_HOME} for USER_HOME because _stargate_home "
            "file exists"
        )
        IS_PORTABLE_INSTALL = True
        PORTABLE_ROOT = USER_HOME
elif IS_LINUX and 'APPIMAGE' in os.environ:
    executable = os.environ['APPIMAGE']
    dirname = os.path.dirname(executable)
    if os.path.isfile(
        os.path.join(dirname, '_stargate_home'),
    ):
        USER_HOME = dirname
        print(
            f"Using {USER_HOME} for USER_HOME because _stargate_home "
            "file exists"
        )
        IS_PORTABLE_INSTALL = True
        PORTABLE_ROOT = USER_HOME

HOME = os.path.join(
    USER_HOME,
    MAJOR_VERSION,
)
DEFAULT_PROJECT_DIR = os.path.join(
    HOME,
    'projects',
)
READY = False
PROJECT_DIR = None
DAW_MAX_SONG_COUNT = 20
DAW_CURRENT_SEQUENCE_UID = 0

IPC_ENABLED = False
IPC_TRANSPORT = None
IPC = None
DAW_IPC = None
WAVE_EDIT_IPC = None

CONFIG_DIR = os.path.join(HOME, "config")
PRESET_DIR = os.path.join(CONFIG_DIR, "preset")
LOG_DIR = os.path.join(HOME, "log")
ENGINE_PIDFILE = os.path.join(HOME, 'engine.pid')
UI_PIDFILE = os.path.join(HOME, 'ui.pid')

for _f_dir in (
    CONFIG_DIR,
    DEFAULT_PROJECT_DIR,
    HOME,
    LOG_DIR,
    PRESET_DIR,
):
    if not os.path.isdir(_f_dir):
        print(f"Creating {_f_dir}")
        os.makedirs(_f_dir)

# Plugins
PLUGINS_PER_TRACK = 10
SENDS_PER_TRACK = 16
TOTAL_PLUGINS_PER_TRACK = PLUGINS_PER_TRACK + SENDS_PER_TRACK

# Projects
PROJECT = None
DAW_PROJECT = None
WAVE_EDIT_PROJECT = None

