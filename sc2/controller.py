"""
Very similar to the client.py it maybe can be absorbed by it
"""
import logging

from s2clientprotocol import sc2api_pb2 as sc_pb

from .player import Computer
from .protocol import Protocol

LOGGER = logging.getLogger(__name__)


class Controller(Protocol):
    """ Groups some leftovers requests to the client """

    def __init__(self, web_server, process):
        super().__init__(web_server)
        self.__process = process

    @property
    def running(self):
        """ Check if the process is running"""
        return self.__process.process is not None

    async def create_game(self, game_map, players, realtime, random_seed=None):
        """ Send the request to the protocol to create the game with the players info """
        if not isinstance(realtime, bool):
            raise AssertionError()
        req = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(map_path=str(game_map.relative_path)), realtime=realtime)
        if random_seed is not None:
            req.random_seed = random_seed

        for player in players:
            player_info = req.player_setup.add()
            player_info.type = player.type.value
            if isinstance(player, Computer):
                player_info.race = player.race.value
                player_info.difficulty = player.difficulty.value
                player_info.ai_build = player.ai_build.value
        request = await self.execute(create_game=req)
        return request

    async def start_replay(self, replay_path, observed_id=0):  # Added
        """
        Play the replay that is on given path
        Parameters
        ----------
        replay_path: Get the replay path
        observed_id: Changes the id of the player1

        Returns
        -------
        True if the request was successful
        """
        interface_options = sc_pb.InterfaceOptions(
            raw=True, score=True, show_cloaked=True, raw_affects_selection=False, raw_crop_to_playable_area=False
        )
        req = sc_pb.RequestStartReplay(
            replay_path=replay_path, observed_player_id=observed_id, options=interface_options
        )

        request = await self.execute(start_replay=req)

        return request
