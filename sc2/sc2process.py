"""
Groups everything related to the processes used by the API and game and how to kill then
changed last: 28/12/2019
"""

import asyncio
import logging
import os.path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, List, Optional

import aiohttp
import portpicker

from sc2 import paths
from sc2.versions import VERSIONS
from .controller import Controller
from .paths import Paths

LOGGER = logging.getLogger(__name__)


class KillSwitch:
    """ Kill the processes"""

    _to_kill: List[Any] = []

    @classmethod
    def add(cls, value):
        """ Add processes that have to be killed"""
        LOGGER.debug("kill_switch: Add switch")
        cls._to_kill.append(value)

    @classmethod
    def kill_all(cls):
        """ Kill all processes that were added by the function above"""
        for process in cls._to_kill:
            process.clean()


class SC2Process:
    """ Houses everything related to the processes used in this API"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
        fullscreen: bool = False,
        render: bool = False,
        sc2_version: str = None,
        base_build: str = None,
        data_hash: str = None,
    ) -> None:
        if not isinstance(host, str):
            raise AssertionError()
        if not (isinstance(port, int) or port is None):
            raise AssertionError()

        self._render = render
        self._fullscreen = fullscreen
        self._host = host
        if port is None:
            self._port = portpicker.pick_unused_port()
        else:
            self._port = port
        self._tmp_dir = tempfile.mkdtemp(prefix="SC2_")
        self.process = None
        self._session = None
        self.web_socket = None
        self._sc2_version = sc2_version
        self._base_build = base_build
        self._data_hash = data_hash

    async def __aenter__(self):
        KillSwitch.add(self)

        # noinspection PyUnusedLocal
        def signal_handler(*args):
            # unused arguments: signal handling library expects all signal
            # callback handlers to accept two positional arguments
            KillSwitch.kill_all()

        signal.signal(signal.SIGINT, signal_handler)

        try:
            self.process = self._launch()
            self.web_socket = await self._connect()
        except Exception as error:
            print(f"An error occurred while trying to launch the process - {error.__traceback__}")
            await self._close_connection()
            self.clean()
            raise

        return Controller(self.web_socket, self)

    async def __aexit__(self, *args):
        KillSwitch.kill_all()
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    @property
    def ws_url(self):
        """ The URL that houses the sc2 API"""
        return f"ws://{self._host}:{self._port}/sc2api"

    @property
    def versions(self):
        """ Opens the versions.json file which origins from
        https://github.com/Blizzard/s2client-proto/blob/master/buildinfo/versions.json """
        return VERSIONS

    def find_data_hash(self, target_sc2_version: str):
        """ Returns the data hash from the matching version string. """
        version: dict
        for version in self.versions:
            if version["label"] == target_sc2_version:
                return version["data-hash"]
        return None

    def _launch(self):
        if self._base_build:
            executable = str(paths.latest_executable(Paths.BASE / "Versions", self._base_build))
        else:
            executable = str(Paths.EXECUTABLE)
        args = paths.get_runner_args(Paths.CWD) + [
            executable,
            "-listen",
            self._host,
            "-port",
            str(self._port),
            "-displayMode",
            "1" if self._fullscreen else "0",
            "-dataDir",
            str(Paths.BASE),
            "-tempDir",
            self._tmp_dir,
        ]
        if self._sc2_version:

            def special_match(string_to_validate: str):
                """ Tests if the specified version is in the versions.py dict. """
                for version in self.versions:
                    if version["label"] == string_to_validate:
                        return True
                return False

            valid_version_string = special_match(self._sc2_version)
            if valid_version_string:
                self._data_hash = self.find_data_hash(self._sc2_version)
                if self._data_hash is None:
                    raise AssertionError(
                        f"StarCraft 2 Client version ({self._sc2_version})"
                        f" was not found inside sc2/versions.py file."
                        f" Please check your spelling or check the versions.py file."
                    )

            else:
                LOGGER.warning(
                    f'The submitted version string in sc2.rungame() function call (sc2_version="{self._sc2_version}") '
                    f"was not found in versions.py. Running latest version instead. "
                )

        if self._data_hash:
            args.extend(["-dataVersion", self._data_hash])

        if self._render:
            args.extend(["-eglpath", "libEGL.so"])

        if LOGGER.getEffectiveLevel() <= logging.DEBUG:
            args.append("-verbose")

        return subprocess.Popen(
            args,
            cwd=(str(Paths.CWD) if Paths.CWD else None),
            # , env=run_config.env
        )

    async def _connect(self):
        for i in range(60):
            if self.process is None:
                # The .clean() was called, clearing the process
                LOGGER.debug("Process cleanup complete, exit")
                sys.exit()

            await asyncio.sleep(1)
            try:
                self._session = aiohttp.ClientSession()
                web_socket = await self._session.ws_connect(self.ws_url, timeout=120)
                # web_socket = await self._session.ws_connect(
                #     self.ws_url, timeout=aiohttp.client_ws.ClientWSTimeout(ws_close=120)
                # )
                LOGGER.debug("Websocket connection ready")
                return web_socket
            except aiohttp.ClientConnectorError:
                await self._session.close()
                if i > 15:
                    LOGGER.debug("Connection refused (startup not complete (yet))")

        LOGGER.debug("Websocket connection to SC2 process timed out")
        raise TimeoutError("Websocket")

    async def _close_connection(self):
        LOGGER.info("Closing connection...")

        if self.web_socket is not None:
            await self.web_socket.close()

        if self._session is not None:
            await self._session.close()

    def clean(self):
        """ Terminates the processes safely"""
        if self.process is not None:
            if self.process.poll() is None:
                for _ in range(3):
                    self.process.terminate()
                    time.sleep(0.5)
                    if not self.process or self.process.poll() is not None:
                        break
                else:
                    self.process.kill()
                    self.process.wait()
                    LOGGER.error("KILLED")

        if os.path.exists(self._tmp_dir):
            shutil.rmtree(self._tmp_dir)

        self.process = None
        self.web_socket = None
