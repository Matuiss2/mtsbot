import logging

from s2clientprotocol import sc2api_pb2 as sc_pb

from .player import Computer
from .protocol import Protocol

LOGGER = logging.getLogger(__name__)


class Controller(Protocol):
    def __init__(self, web_server, process):
        super().__init__(web_server)
        self.__process = process

    @property
    def running(self):
        return self.__process.process is not None

    async def create_game(self, game_map, players, realtime, random_seed=None):
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

        LOGGER.info("Creating new game")
        LOGGER.info(f"Map:     {game_map.name}")
        LOGGER.info(f"Players: {', '.join(str(p) for p in players)}")
        result = await self.execute(create_game=req)
        return result

    async def start_replay(self, replay_path, realtime, observed_id=0):  # Added
        interface_options = sc_pb.InterfaceOptions(
            raw=True, score=True, show_cloaked=True, raw_affects_selection=False, raw_crop_to_playable_area=False
        )
        req = sc_pb.RequestStartReplay(
            replay_path=replay_path, observed_player_id=observed_id, options=interface_options
        )

        result = await self.execute(start_replay=req)

        return result
