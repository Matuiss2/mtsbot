"""
Groups all the actions related to the game(join, watch replay, host, etc) and it's appearance
"""
import asyncio
import json
import logging
import os
import time

import async_timeout
import mpyq
import six
from s2clientprotocol import sc2api_pb2 as sc_pb

from .client import Client
from .data import CREATE_GAME_ERROR, RESULT
from .game_state import GameState
from .player import Bot, Human
from .portconfig import Portconfig
from .protocol import ConnectionAlreadyClosed, ProtocolError
from .sc2process import SC2Process

LOGGER = logging.getLogger(__name__)


class SlidingTimeWindow:
    """ Not sure what it does"""

    def __init__(self, size: int):
        if size <= 0:
            raise AssertionError()

        self.window_size = size
        self.window = []

    def push(self, value: float):
        """ Not sure what it does"""
        self.window = (self.window + [value])[-self.window_size :]

    def clear(self):
        """ Not sure what it does"""
        self.window = []

    @property
    def sum(self) -> float:
        """ Not sure what it does"""
        return sum(self.window)

    @property
    def available(self) -> float:
        """ Not sure what it does"""
        return sum(self.window[1:])

    @property
    def available_fmt(self) -> float:
        """ Not sure what it does"""
        return ",".join(f"{w:.2f}" for w in self.window[1:])


async def _play_game_human(client, player_id, realtime, game_time_limit):
    while True:
        state = await client.observation()
        if client.game_result:
            return client.game_result[player_id]

        if game_time_limit and (state.observation.observation.game_loop * 0.725 * (1 / 16)) > game_time_limit:
            print(state.observation.game_loop, state.observation.game_loop * 0.14)
            return RESULT.Tie

        if not realtime:
            await client.step()


async def _play_game_ai(client, player_id, ai, realtime, step_time_limit, game_time_limit):
    if realtime:
        if step_time_limit is not None:
            raise AssertionError()

    # step_time_limit works like this:
    # * If None, then step time is not limited
    # * If given integer or float, the bot will simply resign if any step takes longer than that
    # * Otherwise step_time_limit must be an object, with following settings:
    #
    # Key         | Value      | Description
    # ------------|------------|-------------
    # penalty     | None       | No penalty, the bot can continue on next step
    # penalty     | N: int     | Cooldown penalty, BotAI.on_step will not be called for N steps
    # penalty     | "resign"   | Bot resigns when going over time limit
    # time_limit  | int/float  | Time limit for a single step
    # window_size | N: int     | The time limit will be used for last N steps, instead of 1
    #
    # Cooldown is a harsh penalty. The both loses the ability to act, but even worse,
    # the observation data from skipped steps is also lost. It's like falling asleep in
    # a middle of the game.
    time_penalty_cooldown = 0
    if step_time_limit is None:
        time_limit = None
        time_window = None
        time_penalty = None
    elif isinstance(step_time_limit, (int, float)):
        time_limit = float(step_time_limit)
        time_window = SlidingTimeWindow(1)
        time_penalty = "resign"
    else:
        if not isinstance(step_time_limit, dict):
            raise AssertionError()
        time_penalty = step_time_limit.get("penalty", None)
        time_window = SlidingTimeWindow(int(step_time_limit.get("window_size", 1)))
        time_limit = float(step_time_limit.get("time_limit", None))

    ai.initialize_variables()

    game_data = await client.get_game_data()
    game_info = await client.get_game_info()

    ai.prepare_start(client, player_id, game_info, game_data, realtime=realtime)
    state = await client.observation()
    if client.game_result:
        await ai.on_end(client.game_result[player_id])
        return client.game_result[player_id]
    game_state = GameState(state.observation)
    proto_game_info = await client.execute(game_info=sc_pb.RequestGameInfo())
    ai.prepare_step(game_state, proto_game_info)
    await ai.on_before_start()
    ai.prepare_first_step()
    try:
        await ai.on_start()
    except Exception as error:
        LOGGER.exception(f"AI on_start threw an error - {error.__traceback__}")
        LOGGER.error(f"resigning due to previous error")
        await ai.on_end(RESULT.Defeat)
        return RESULT.Defeat

    iteration = 0
    while True:
        if iteration:
            if realtime:
                state = await client.observation(game_state.game_loop + client.game_step)
            else:
                state = await client.observation()
            if client.game_result:
                try:
                    await ai.on_end(client.game_result[player_id])
                except TypeError:
                    return client.game_result[player_id]
                return client.game_result[player_id]
            game_state = GameState(state.observation)
            LOGGER.debug(f"Score: {game_state.score.score}")

            if game_time_limit and (game_state.game_loop * 0.725 * (1 / 16)) > game_time_limit:
                await ai.on_end(RESULT.Tie)
                return RESULT.Tie
            proto_game_info = await client.execute(game_info=sc_pb.RequestGameInfo())
            ai.prepare_step(game_state, proto_game_info)

        LOGGER.debug(f"Running AI step, it={iteration} {game_state.game_loop * 0.725 * (1 / 16):.2f}s")

        try:
            if realtime:
                await ai.issue_events()
                await ai.on_step(iteration)
                await ai.after_step()
            else:
                if time_penalty_cooldown > 0:
                    time_penalty_cooldown -= 1
                    LOGGER.warning(f"Running AI step: penalty cooldown: {time_penalty_cooldown}")
                    iteration -= 1
                elif time_limit is None:
                    await ai.issue_events()
                    await ai.on_step(iteration)
                    await ai.after_step()
                else:
                    out_of_budget = False
                    budget = time_limit - time_window.available

                    ai.time_budget_available = budget

                    if budget < 0:
                        LOGGER.warning(f"Running AI step: out of budget before step")
                        step_time = 0.0
                        out_of_budget = True
                    else:
                        step_start = time.monotonic()
                        try:
                            async with async_timeout.timeout(budget):
                                await ai.issue_events()
                                await ai.on_step(iteration)
                        except asyncio.TimeoutError:
                            step_time = time.monotonic() - step_start
                            LOGGER.warning(
                                f"Running AI step: out of budget; "
                                + f"budget={budget:.2f}, steptime={step_time:.2f}, "
                                + f"window={time_window.available_fmt}"
                            )
                            out_of_budget = True
                        step_time = time.monotonic() - step_start

                    time_window.push(step_time)

                    if out_of_budget and time_penalty is not None:
                        if time_penalty == "resign":
                            raise RuntimeError("Out of time")
                        time_penalty_cooldown = int(time_penalty)
                        time_window.clear()

                    await ai.after_step()
        except Exception as error:
            if isinstance(error, ProtocolError) and error.is_game_over_error:
                if realtime:
                    return None
                result = client.game_result[player_id]
                if result is None:
                    LOGGER.error("Game over, but no results gathered")
                    raise
                await ai.on_end(result)
                return result
            LOGGER.exception(f"AI step threw an error")  # DO NOT EDIT!
            LOGGER.error(f"Error: {error}")
            LOGGER.error(f"Resigning due to previous error")
            try:
                await ai.on_end(RESULT.Defeat)
            except TypeError:
                return RESULT.Defeat
            return RESULT.Defeat

        LOGGER.debug(f"Running AI step: done")

        if not realtime:
            if not client.in_game:
                await ai.on_end(client.game_result[player_id])
                return client.game_result[player_id]

            await client.step()

        iteration += 1


async def play_game(
    player, client, realtime, portconfig, step_time_limit=None, game_time_limit=None, rgb_render_config=None
):
    """ Join the client to play a game vs human or vs ai"""
    if not isinstance(realtime, bool):
        raise AssertionError(repr(realtime))

    player_id = await client.join_game(
        player.name, player.race, portconfig=portconfig, rgb_render_config=rgb_render_config
    )

    if isinstance(player, Human):
        result = await _play_game_human(client, player_id, realtime, game_time_limit)
    else:
        result = await _play_game_ai(client, player_id, player.ai, realtime, step_time_limit, game_time_limit)

    return result


async def _play_replay(client, ai, realtime=False, player_id=0):
    ai.initialize_variables()

    game_data = await client.get_game_data()
    game_info = await client.get_game_info()
    client.game_step = 1
    ai.prepare_start(client, player_id, game_info, game_data, realtime=realtime)
    state = await client.observation()
    if client.game_result:
        await ai.on_end(client.game_result[player_id])
        return client.game_result[player_id]
    game_state = GameState(state.observation)
    proto_game_info = await client.execute(game_info=sc_pb.RequestGameInfo())
    ai.prepare_step(game_state, proto_game_info)
    ai.prepare_first_step()
    try:
        await ai.on_start()
    except Exception as error:
        LOGGER.exception(f"AI on_start threw an error - {error.__traceback__}")
        LOGGER.error(f"resigning due to previous error")
        await ai.on_end(RESULT.Defeat)
        return RESULT.Defeat

    iteration = 0
    while True:
        if iteration:
            if realtime:
                state = await client.observation(game_state.game_loop + client.game_step)
            else:
                state = await client.observation()
            if client.game_result:
                try:
                    await ai.on_end(client.game_result[player_id])
                except TypeError:
                    return client.game_result[player_id]
                return client.game_result[player_id]
            game_state = GameState(state.observation)
            LOGGER.debug(f"Score: {game_state.score.score}")

            proto_game_info = await client.execute(game_info=sc_pb.RequestGameInfo())
            ai.prepare_step(game_state, proto_game_info)

        LOGGER.debug(f"Running AI step, it={iteration} {game_state.game_loop * 0.725 * (1 / 16):.2f}s")

        try:
            if realtime:
                await ai.issue_events()
                await ai.on_step(iteration)
                await ai.after_step()
            else:
                await ai.issue_events()
                await ai.on_step(iteration)
                await ai.after_step()

        except Exception as error:
            if isinstance(error, ProtocolError) and error.is_game_over_error:
                if realtime:
                    return None
                await ai.on_end(RESULT.Victory)
                return None
            LOGGER.exception(f"AI step threw an error")  # DO NOT EDIT!
            LOGGER.error(f"Error: {error}")
            LOGGER.error(f"Resigning due to previous error")
            try:
                await ai.on_end(RESULT.Defeat)
            except TypeError:
                return RESULT.Defeat
            return RESULT.Defeat

        LOGGER.debug(f"Running AI step: done")

        if not realtime:
            if not client.in_game:
                await ai.on_end(RESULT.Victory)
                return RESULT.Victory

        await client.step()

        iteration += 1


async def _setup_host_game(server, map_settings, players, realtime, random_seed=None):
    create_game_request = await server.create_game(map_settings, players, realtime, random_seed)
    if create_game_request.create_game.HasField("error"):
        err = f"Could not create game: {CREATE_GAME_ERROR(create_game_request.create_game.error)}"
        if create_game_request.create_game.HasField("error_details"):
            err += f": {create_game_request.create_game.error_details}"
        LOGGER.critical(err)
        raise RuntimeError(err)

    return Client(server.web_server)


async def _host_game(
    map_settings,
    players,
    realtime,
    portconfig=None,
    save_replay_as=None,
    step_time_limit=None,
    game_time_limit=None,
    rgb_render_config=None,
    random_seed=None,
    sc2_version=None,
):

    if not players:
        raise AssertionError("Can't create a game without players")

    if not any(isinstance(p, (Human, Bot)) for p in players):
        raise AssertionError()

    async with SC2Process(
        fullscreen=players[0].fullscreen, render=rgb_render_config is not None, sc2_version=sc2_version
    ) as server:
        await server.ping()

        client = await _setup_host_game(server, map_settings, players, realtime, random_seed)
        if not isinstance(players[0], Human) and getattr(players[0].ai, "raw_affects_selection", None) is not None:
            client.raw_affects_selection = players[0].ai.raw_affects_selection

        try:
            result = await play_game(
                players[0], client, realtime, portconfig, step_time_limit, game_time_limit, rgb_render_config
            )
            if save_replay_as is not None:
                await client.save_replay(save_replay_as)
            await client.leave()
            await client.quit()
        except ConnectionAlreadyClosed:
            logging.error(f"Connection was closed before the game ended")
            return None

        return result


async def _host_game_aiter(
    map_settings, players, realtime, portconfig=None, save_replay_as=None, step_time_limit=None, game_time_limit=None,
):
    if not players:
        raise AssertionError("Can't create a game without players")

    if not any(isinstance(p, (Human, Bot)) for p in players):
        raise AssertionError()

    async with SC2Process() as server:
        while True:
            await server.ping()

            client = await _setup_host_game(server, map_settings, players, realtime)
            if not isinstance(players[0], Human) and getattr(players[0].ai, "raw_affects_selection", None) is not None:
                client.raw_affects_selection = players[0].ai.raw_affects_selection

            try:
                result = await play_game(players[0], client, realtime, portconfig, step_time_limit, game_time_limit)

                if save_replay_as is not None:
                    await client.save_replay(save_replay_as)
                await client.leave()
            except ConnectionAlreadyClosed:
                logging.error(f"Connection was closed before the game ended")
                return

            new_players = yield result
            if new_players is not None:
                players = new_players


def _host_game_iter(*args, **kwargs):
    game = _host_game_aiter(*args, **kwargs)
    new_player_configuration = None
    while True:
        new_player_configuration = yield asyncio.get_event_loop().run_until_complete(
            game.asend(new_player_configuration)
        )


async def _join_game(
    players, realtime, portconfig, save_replay_as=None, step_time_limit=None, game_time_limit=None,
):
    async with SC2Process(fullscreen=players[1].fullscreen) as server:
        await server.ping()

        client = Client(server.ws)
        if not isinstance(players[1], Human) and getattr(players[1].ai, "raw_affects_selection", None) is not None:
            client.raw_affects_selection = players[1].ai.raw_affects_selection

        try:
            result = await play_game(players[1], client, realtime, portconfig, step_time_limit, game_time_limit)
            if save_replay_as is not None:
                await client.save_replay(save_replay_as)
            await client.leave()
            await client.quit()
        except ConnectionAlreadyClosed:
            logging.error(f"Connection was closed before the game ended")
            return None

        return result


async def _setup_replay(server, replay_path, realtime, observed_id):
    await server.start_replay(replay_path, realtime, observed_id)
    return Client(server.ws)


async def _host_replay(replay_path, ai, realtime, base_build, data_version, observed_id):
    async with SC2Process(fullscreen=False, base_build=base_build, data_hash=data_version) as server:
        await server.ping()
        client = await _setup_replay(server, replay_path, realtime, observed_id)
        result = await _play_replay(client, ai, realtime)
        return result


def get_replay_version(replay_path):
    """ Get the Sc2 patch version where this replay game was played """
    with open(replay_path, "rb") as file:
        replay_data = file.read()
        replay_io = six.BytesIO()
        replay_io.write(replay_data)
        replay_io.seek(0)
        archive = mpyq.MPQArchive(replay_io).extract()
        metadata = json.loads(archive[b"replay.gamemetadata.json"].decode("utf-8"))
        return metadata["BaseBuild"], metadata["DataVersion"]


def run_game(map_settings, players, **kwargs):
    """ Last level request to start the game"""
    if sum(isinstance(p, (Human, Bot)) for p in players) > 1:
        host_only_args = ["save_replay_as", "rgb_render_config", "random_seed", "sc2_version"]
        join_kwargs = {k: v for k, v in kwargs.items() if k not in host_only_args}

        portconfig = Portconfig()
        request = asyncio.get_event_loop().run_until_complete(
            asyncio.gather(
                _host_game(map_settings, players, **kwargs, portconfig=portconfig),
                _join_game(players, **join_kwargs, portconfig=portconfig),
            )
        )
    else:
        request = asyncio.get_event_loop().run_until_complete(_host_game(map_settings, players, **kwargs))
    return request


def run_replay(ai, replay_path, realtime=False, observed_id=0):
    """ Last level request to start the replay"""
    if not os.path.isfile(replay_path):
        raise AssertionError(f"Replay does not exist at the given path: {replay_path}")
    if not os.path.isabs(replay_path):
        raise AssertionError(
            f"Replay path has to be an absolute path,"
            f' e.g. "C:/replays/my_replay.SC2Replay" but given path was "{replay_path}"'
        )
    base_build, data_version = get_replay_version(replay_path)
    request = asyncio.get_event_loop().run_until_complete(
        _host_replay(replay_path, ai, realtime, base_build, data_version, observed_id)
    )
    return request
