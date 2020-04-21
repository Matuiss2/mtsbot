"""
It tries to get all the paths that this API will use
changed last: 27/12/2019
"""
import logging
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)

BASEDIR = {
    "Windows": "C:/Program Files (x86)/StarCraft II",
    "Darwin": "/Applications/StarCraft II",
    "Linux": "~/StarCraftII",
    "WineLinux": "~/.wine/drive_c/Program Files (x86)/StarCraft II",
}

USERPATH = {
    "Windows": "\\Documents\\StarCraft II\\ExecuteInfo.txt",
    "Darwin": "/Library/Application Support/Blizzard/StarCraft II/ExecuteInfo.txt",
    "Linux": None,
    "WineLinux": None,
}

BINPATH = {
    "Windows": "SC2_x64.exe",
    "Darwin": "SC2.app/Contents/MacOS/SC2",
    "Linux": "SC2_x64",
    "WineLinux": "SC2_x64.exe",
}

CWD = {"Windows": "Support64", "Darwin": None, "Linux": None, "WineLinux": "Support64"}

PF = os.environ.get("SC2PF", platform.system())


def get_runner_args(cwd):
    """Get it to work on linux"""
    if "WINE" in os.environ:
        runner_dir = os.path.dirname(os.environ.get("WINE"))
        win_cwd = subprocess.run(
            [os.path.join(runner_dir, "winepath"), "-w", cwd], capture_output=True, text=True, check=True
        ).stdout.rstrip()
        return [os.environ.get("WINE"), "start", "/d", win_cwd, "/unix"]

    return []


def latest_executable(versions_dir, base_build=None):
    """ Returns the path to the latest sc2 binary"""
    if base_build is None:
        latest = max((int(p.name[4:]), p) for p in versions_dir.iterdir() if p.is_dir() and p.name.startswith("Base"))
    else:
        latest = (
            int(base_build[4:]),
            max(p for p in versions_dir.iterdir() if p.is_dir() and p.name.startswith(str(base_build))),
        )
    version, path = latest

    if version < 55958:
        LOGGER.critical(f"Your SC2 binary is too old. Upgrade to 3.16.1 or newer.")
        sys.exit()
    return path / BINPATH[PF]


class _MetaPaths(type):
    """"Lazily loads paths to allow importing the library even if SC2 isn't installed."""

    def setup(cls):
        if PF not in BASEDIR:
            LOGGER.critical(f"Unsupported platform '{PF}'")
            sys.exit()

        try:
            base = os.environ.get("SC2PATH")
            if base is None and USERPATH[PF] is not None:
                executable_info = str(Path.home().expanduser()) + USERPATH[PF]
                if os.path.isfile(executable_info):
                    with open(executable_info) as sc2_info:
                        content = sc2_info.read()
                    if content:
                        base = re.search(r" = (.*)Versions", content).group(1)
                        if not os.path.exists(base):
                            base = None
            if base is None:
                base = BASEDIR[PF]
            cls.BASE = Path(base).expanduser()
            cls.EXECUTABLE = latest_executable(cls.BASE / "Versions")
            cls.CWD = cls.BASE / CWD[PF] if CWD[PF] else None

            cls.REPLAYS = cls.BASE / "Replays"

            if (cls.BASE / "maps").exists():
                cls.MAPS = cls.BASE / "maps"
            else:
                cls.MAPS = cls.BASE / "Maps"
        except FileNotFoundError as error:
            LOGGER.critical(f"SC2 installation not found: File '{error.filename}' does not exist.")
            sys.exit()

    def __getattr__(cls, attr):
        cls().setup()
        return getattr(cls, attr)


class Paths(metaclass=_MetaPaths):
    """Paths for SC2 folders, lazily loaded using the above metaclass."""
