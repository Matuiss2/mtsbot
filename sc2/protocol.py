"""
Groups the last level connection to the sc2 protocol and the errors related to that
"""
import asyncio
import logging
import sys
from contextlib import suppress

from s2clientprotocol import sc2api_pb2 as sc_pb

from .data import STATUS

LOGGER = logging.getLogger(__name__)


class ProtocolError(Exception):
    """ Groups the errors that happens when 'talking' to thew protocol """

    @property
    def is_game_over_error(self) -> bool:
        """If the game ended connecting to the protocol is not needed"""
        return self.args[0] in ["['Game has already ended']", "['Not supported if game has already ended']"]


class ConnectionAlreadyClosed(ProtocolError):
    """ Extension to the protocol error...its empty, so maybe absorb this as a method from protocol error """


class Protocol:
    """ Handles the connection and the requests to the protocol"""

    def __init__(self, web_server):
        """
        :param web_server:
        """
        if not web_server:
            raise AssertionError()
        self.web_server = web_server
        self._status = None

    async def __request(self, request):
        LOGGER.debug(f"Sending request: {request !r}")
        try:
            await self.web_server.send_bytes(request.SerializeToString())
        except TypeError:
            LOGGER.exception("Cannot send: Connection already closed.")
            raise ConnectionAlreadyClosed("Connection already closed.")
        LOGGER.debug(f"Request sent")

        response = sc_pb.Response()
        try:
            response_bytes = await self.web_server.receive_bytes()
        except TypeError:
            LOGGER.info("Cannot receive: Connection already closed.")
            sys.exit(2)
        except asyncio.CancelledError:
            try:
                await self.web_server.receive_bytes()
            except asyncio.CancelledError:
                LOGGER.critical("Requests must not be cancelled multiple times")
                sys.exit(2)
            raise

        response.ParseFromString(response_bytes)
        LOGGER.debug(f"Response received")
        return response

    async def execute(self, **kwargs):
        """ Execute the request calls"""
        if len(kwargs) != 1:
            raise AssertionError("Only one request allowed")

        request = sc_pb.Request(**kwargs)

        response = await self.__request(request)

        new_status = STATUS(response.status)
        self._status = new_status

        if response.error:
            LOGGER.debug(f"Response contained an error: {response.error}")
            raise ProtocolError(f"{response.error}")

        return response

    async def ping(self):
        """ Request the ping from the protocol"""
        result = await self.execute(ping=sc_pb.RequestPing())
        return result

    async def quit(self):
        """ Request to close the connection from the protocol"""
        with suppress(ConnectionAlreadyClosed):
            await self.execute(quit=sc_pb.RequestQuit())
