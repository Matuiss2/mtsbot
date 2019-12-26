from __future__ import annotations
import logging
from typing import Iterable, List, Optional, Set, Tuple, Union

from s2clientprotocol import common_pb2 as common_pb
from s2clientprotocol import debug_pb2 as debug_pb
from s2clientprotocol import query_pb2 as query_pb
from s2clientprotocol import raw_pb2 as raw_pb
from s2clientprotocol import sc2api_pb2 as sc_pb

from .action import combine_actions
from .data import ActionResult, ChatChannel, Race, Result, Status
from .game_data import AbilityData, GameData
from .game_info import GameInfo
from .ids.ability_id import AbilityId
from .ids.unit_typeid import UnitTypeId
from .position import Point2, Point3
from .protocol import Protocol, ProtocolError
from .renderer import Renderer
from .unit import Unit
from .units import Units

logger = logging.getLogger(__name__)


class Client(Protocol):
    def __init__(self, ws):
        """
        :param ws:
        """
        super().__init__(ws)
        # How many frames will be waited between iterations before the next one is called
        self.game_step = 8
        self._player_id = None
        self.game_result = None
        # Store a hash value of all the debug requests to prevent sending the same ones again if they haven't changed
        # last frame
        self._debug_hash_tuple_last_iteration: Tuple[int, int, int, int] = (0, 0, 0, 0)
        self._debug_draw_last_frame = False
        self._debug_texts = []
        self._debug_lines = []
        self._debug_boxes = []
        self._debug_spheres = []

        self._renderer = None
        self.raw_affects_selection = False

    @property
    def in_game(self):
        return self._status in {Status.in_game, Status.in_replay}

    async def join_game(self, name=None, race=None, observed_player_id=None, portconfig=None, rgb_render_config=None):
        interface_options = sc_pb.InterfaceOptions(
            raw=True,
            score=True,
            show_cloaked=True,
            raw_affects_selection=self.raw_affects_selection,
            raw_crop_to_playable_area=False,
        )

        if rgb_render_config:
            if not isinstance(rgb_render_config, dict):
                raise AssertionError()
            if "window_size" not in rgb_render_config and "minimap_size" not in rgb_render_config:
                raise AssertionError()
            window_size = rgb_render_config["window_size"]
            minimap_size = rgb_render_config["minimap_size"]
            self._renderer = Renderer(self, window_size, minimap_size)
            map_width, map_height = window_size
            minimap_width, minimap_height = minimap_size

            interface_options.render.resolution.x = map_width
            interface_options.render.resolution.y = map_height
            interface_options.render.minimap_resolution.x = minimap_width
            interface_options.render.minimap_resolution.y = minimap_height

        if race is None:
            if not isinstance(observed_player_id, int):
                raise AssertionError(f"observed_player_id is of type {type(observed_player_id)}")
            # join as observer
            req = sc_pb.RequestJoinGame(observed_player_id=observed_player_id, options=interface_options)
        else:
            if not isinstance(race, Race):
                raise AssertionError()
            req = sc_pb.RequestJoinGame(race=race.value, options=interface_options)

        if portconfig:
            req.shared_port = portconfig.shared
            req.server_ports.game_port = portconfig.server[0]
            req.server_ports.base_port = portconfig.server[1]

            for ppc in portconfig.players:
                p = req.client_ports.add()
                p.game_port = ppc[0]
                p.base_port = ppc[1]

        if name is not None:
            if not isinstance(name, str):
                raise AssertionError(f"name is of type {type(name)}")
            req.player_name = name

        result = await self.execute(join_game=req)
        self.game_result = None
        self._player_id = result.join_game.player_id
        return result.join_game.player_id

    async def leave(self):
        """ You can use 'await self._client.leave()' to surrender midst game. """
        is_resign = self.game_result is None

        if is_resign:
            # For all clients that can leave, result of leaving the game either
            # loss, or the client will ignore the result
            self.game_result = {self._player_id: Result.Defeat}

        try:
            await self.execute(leave_game=sc_pb.RequestLeaveGame())
        except ProtocolError:
            if is_resign:
                raise

    async def save_replay(self, path):
        logger.debug(f"Requesting replay from server")
        result = await self.execute(save_replay=sc_pb.RequestSaveReplay())
        with open(path, "wb") as f:
            f.write(result.save_replay.data)
        logger.info(f"Saved replay to {path}")

    async def observation(self, game_loop=None):
        if game_loop is not None:
            result = await self.execute(observation=sc_pb.RequestObservation(game_loop=game_loop))
        else:
            result = await self.execute(observation=sc_pb.RequestObservation())
        if not result.HasField("observation"):
            raise AssertionError()

        if not self.in_game or result.observation.player_result:
            # Sometimes game ends one step before results are available
            if not result.observation.player_result:
                result = await self.execute(observation=sc_pb.RequestObservation())
                if not result.observation.player_result:
                    raise AssertionError()

            player_id_to_result = {}
            for pr in result.observation.player_result:
                player_id_to_result[pr.player_id] = Result(pr.result)
            self.game_result = player_id_to_result

        # if render_data is available, then RGB rendering was requested
        if self._renderer and result.observation.observation.HasField("render_data"):
            await self._renderer.render(result.observation)

        return result

    async def step(self, step_size: int = None):
        """ EXPERIMENTAL: Change self._client.game_step during the step function to increase or decrease steps per
        second """
        step_size = step_size or self.game_step
        return await self.execute(step=sc_pb.RequestStep(count=step_size))

    async def get_game_data(self) -> GameData:
        result = await self.execute(
            data=sc_pb.RequestData(ability_id=True, unit_type_id=True, upgrade_id=True, buff_id=True, effect_id=True)
        )
        return GameData(result.data)

    async def dump_data(self, ability_id=True, unit_type_id=True, upgrade_id=True, buff_id=True, effect_id=True):
        """
        Dump the game data files
        choose what data to dump in the keywords
        this function writes to a text file
        call it one time in on_step with:
        await self._client.dump_data()
        """
        result = await self.execute(
            data=sc_pb.RequestData(
                ability_id=ability_id,
                unit_type_id=unit_type_id,
                upgrade_id=upgrade_id,
                buff_id=buff_id,
                effect_id=effect_id,
            )
        )
        with open("data_dump.txt", "a") as file:
            file.write(str(result.data))

    async def get_game_info(self) -> GameInfo:
        result = await self.execute(game_info=sc_pb.RequestGameInfo())
        return GameInfo(result.game_info)

    async def actions(self, actions, return_successes=False):
        if not actions:
            return None
        if not isinstance(actions, list):
            actions = [actions]
        res = await self.execute(
            action=sc_pb.RequestAction(actions=(sc_pb.Action(action_raw=a) for a in combine_actions(actions)))
        )
        if return_successes:
            return [ActionResult(r) for r in res.action.result]
        return [ActionResult(r) for r in res.action.result if ActionResult(r) != ActionResult.Success]

    async def query_pathway(
        self, start: Union[Unit, Point2, Point3], end: Union[Point2, Point3]
    ) -> Optional[Union[int, float]]:
        """ Caution: returns "None" when path not found
        Try to combine queries with the function below because the pathway query is generally slow.

        :param start:
        :param end: """
        if not isinstance(start, (Point2, Unit)):
            raise AssertionError()
        if not isinstance(end, Point2):
            raise AssertionError()
        if isinstance(start, Point2):
            result = await self.execute(
                query=query_pb.RequestQuery(
                    pathing=[
                        query_pb.RequestQueryPathing(
                            start_pos=common_pb.Point2D(x=start.x, y=start.y),
                            end_pos=common_pb.Point2D(x=end.x, y=end.y),
                        )
                    ]
                )
            )
        else:
            result = await self.execute(
                query=query_pb.RequestQuery(
                    pathing=[
                        query_pb.RequestQueryPathing(unit_tag=start.tag, end_pos=common_pb.Point2D(x=end.x, y=end.y))
                    ]
                )
            )
        distance = float(result.query.pathing[0].distance)
        if distance <= 0.0:
            return None
        return distance

    async def query_pathways(self, zipped_list: List[List[Union[Unit, Point2, Point3]]]) -> List[Union[float, int]]:
        """ Usage: await self.query_pathways([[unit1, target2], [unit2, target2]])
        -> returns [distance1, distance2]
        Caution: returns 0 when path not found

        :param zipped_list:
        """
        if not zipped_list:
            raise AssertionError("No zipped_list")
        if not isinstance(zipped_list, list):
            raise AssertionError(f"{type(zipped_list)}")
        if not isinstance(zipped_list[0], list):
            raise AssertionError(f"{type(zipped_list[0])}")
        if len(zipped_list[0]) != 2:
            raise AssertionError(f"{len(zipped_list[0])}")
        if not isinstance(zipped_list[0][0], (Point2, Unit)):
            raise AssertionError(f"{type(zipped_list[0][0])}")
        if not isinstance(zipped_list[0][1], Point2):
            raise AssertionError(f"{type(zipped_list[0][1])}")
        if isinstance(zipped_list[0][0], Point2):
            results = await self.execute(
                query=query_pb.RequestQuery(
                    pathing=(
                        query_pb.RequestQueryPathing(
                            start_pos=common_pb.Point2D(x=p1.x, y=p1.y), end_pos=common_pb.Point2D(x=p2.x, y=p2.y)
                        )
                        for p1, p2 in zipped_list
                    )
                )
            )
        else:
            results = await self.execute(
                query=query_pb.RequestQuery(
                    pathing=(
                        query_pb.RequestQueryPathing(unit_tag=p1.tag, end_pos=common_pb.Point2D(x=p2.x, y=p2.y))
                        for p1, p2 in zipped_list
                    )
                )
            )
        return [float(d.distance) for d in results.query.pathing]

    async def query_building_placement(
        self, ability: AbilityData, positions: List[Union[Point2, Point3]], ignore_resources: bool = True
    ) -> List[ActionResult]:
        if not isinstance(ability, AbilityData):
            raise AssertionError()
        result = await self.execute(
            query=query_pb.RequestQuery(
                placements=(
                    query_pb.RequestQueryBuildingPlacement(
                        ability_id=ability.id.value, target_pos=common_pb.Point2D(x=position.x, y=position.y)
                    )
                    for position in positions
                ),
                ignore_resource_requirements=ignore_resources,
            )
        )
        return [ActionResult(p.result) for p in result.query.placements]

    async def query_available_abilities(
        self, units: Union[List[Unit], Units], ignore_resource_requirements: bool = False
    ) -> List[List[AbilityId]]:
        """ Query abilities of multiple units """
        input_was_a_list = True
        if not isinstance(units, list):
            # Deprecated, accepting a single unit may be removed in the future, query a list of units instead
            if not isinstance(units, Unit):
                raise AssertionError()
            units = [units]
            input_was_a_list = False
        if not units:
            raise AssertionError()
        result = await self.execute(
            query=query_pb.RequestQuery(
                abilities=(query_pb.RequestQueryAvailableAbilities(unit_tag=unit.tag) for unit in units),
                ignore_resource_requirements=ignore_resource_requirements,
            )
        )
        # Fix for bots that only query a single unit, may be removed soon
        if not input_was_a_list:
            return [[AbilityId(a.ability_id) for a in b.abilities] for b in result.query.abilities][0]
        return [[AbilityId(a.ability_id) for a in b.abilities] for b in result.query.abilities]

    async def chat_send(self, message: str, team_only: bool):
        """ Writes a message to the chat """
        ch = ChatChannel.Team if team_only else ChatChannel.Broadcast
        await self.execute(
            action=sc_pb.RequestAction(
                actions=[sc_pb.Action(action_chat=sc_pb.ActionChat(channel=ch.value, message=message))]
            )
        )

    async def toggle_autocast(self, units: Union[List[Unit], Units], ability: AbilityId):
        """ Toggle autocast of all specified units

        :param units:
        :param ability: """
        if not units:
            raise AssertionError()
        if not isinstance(units, list):
            raise AssertionError()
        if not all(isinstance(u, Unit) for u in units):
            raise AssertionError()
        if not isinstance(ability, AbilityId):
            raise AssertionError()

        await self.execute(
            action=sc_pb.RequestAction(
                actions=[
                    sc_pb.Action(
                        action_raw=raw_pb.ActionRaw(
                            toggle_autocast=raw_pb.ActionRawToggleAutocast(
                                ability_id=ability.value, unit_tags=(u.tag for u in units)
                            )
                        )
                    )
                ]
            )
        )

    async def debug_create_unit(self, unit_spawn_commands: List[List[Union[UnitTypeId, int, Point2, Point3]]]):
        """ Usage example (will spawn 5 marines in the center of the map for player ID 1):
        await self._client.debug_create_unit([[UnitTypeId.MARINE, 5, self._game_info.map_center, 1]])

        :param unit_spawn_commands: """
        if not isinstance(unit_spawn_commands, list):
            raise AssertionError()
        if not unit_spawn_commands:
            raise AssertionError()
        if not isinstance(unit_spawn_commands[0], list):
            raise AssertionError()
        if not len(unit_spawn_commands[0]) != 4:
            raise AssertionError()
        if not isinstance(unit_spawn_commands[0][0], UnitTypeId):
            raise AssertionError()
        if unit_spawn_commands[0][1] <= 0:
            raise AssertionError()
        if not isinstance(unit_spawn_commands[0][2], (Point2, Point3)):
            raise AssertionError()
        if not 1 <= unit_spawn_commands[0][3] <= 2:
            raise AssertionError()

        await self.execute(
            debug=sc_pb.RequestDebug(
                debug=(
                    debug_pb.DebugCommand(
                        create_unit=debug_pb.DebugCreateUnit(
                            unit_type=unit_type.value,
                            owner=owner_id,
                            pos=common_pb.Point2D(x=position.x, y=position.y),
                            quantity=amount_of_units,
                        )
                    )
                    for unit_type, amount_of_units, position, owner_id in unit_spawn_commands
                )
            )
        )

    async def debug_kill_unit(self, unit_tags: Union[Unit, Units, List[int], Set[int]]):
        """
        :param unit_tags:
        """
        if isinstance(unit_tags, Units):
            unit_tags = unit_tags.tags
        if isinstance(unit_tags, Unit):
            unit_tags = [unit_tags.tag]
        if not unit_tags:
            raise AssertionError()

        await self.execute(
            debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(kill_unit=debug_pb.DebugKillUnit(tag=unit_tags))])
        )

    async def move_camera(self, position: Union[Unit, Units, Point2, Point3]):
        """ Moves camera to the target position """
        if not isinstance(position, (Unit, Units, Point2, Point3)):
            raise AssertionError()
        if isinstance(position, Units):
            position = position.center
        if isinstance(position, Unit):
            position = position.position
        await self.execute(
            action=sc_pb.RequestAction(
                actions=[
                    sc_pb.Action(
                        action_raw=raw_pb.ActionRaw(
                            camera_move=raw_pb.ActionRawCameraMove(
                                center_world_space=common_pb.Point(x=position.x, y=position.y)
                            )
                        )
                    )
                ]
            )
        )

    async def obs_move_camera(self, position: Union[Unit, Units, Point2, Point3]):
        """ Moves observer camera to the target position """
        if not isinstance(position, (Unit, Units, Point2, Point3)):
            raise AssertionError()
        if isinstance(position, Units):
            position = position.center
        if isinstance(position, Unit):
            position = position.position
        await self.execute(
            obs_action=sc_pb.RequestObserverAction(
                actions=[
                    sc_pb.ObserverAction(
                        camera_move=sc_pb.ActionObserverCameraMove(
                            world_pos=common_pb.Point2D(x=position.x, y=position.y)
                        )
                    )
                ]
            )
        )

    async def move_camera_spatial(self, position: Union[Point2, Point3]):
        """ Moves camera to the target position using the spatial action interface

        :param position: """
        from s2clientprotocol import spatial_pb2 as spatial_pb

        if not isinstance(position, (Point2, Point3)):
            raise AssertionError()
        action = sc_pb.Action(
            action_render=spatial_pb.ActionSpatial(
                camera_move=spatial_pb.ActionSpatialCameraMove(
                    center_minimap=common_pb.PointI(x=position.x, y=position.y)
                )
            )
        )
        await self.execute(action=sc_pb.RequestAction(actions=[action]))

    def debug_text_simple(self, text: str):
        """ Draws a text in the top left corner of the screen (up to a max of 6 messages fit there). """
        self._debug_texts.append(DrawItemScreenText(text=text, color=None, start_point=Point2((0, 0)), font_size=8))

    def debug_text_screen(
        self,
        text: str,
        pos: Union[Point2, Point3, tuple, list],
        color: Union[tuple, list, Point3] = None,
        size: int = 8,
    ):
        """ Draws a text on the screen (monitor / game window) with coordinates 0 <= x, y <= 1. """
        if len(pos) < 2:
            raise AssertionError()
        if not 0 <= pos[0] <= 1:
            raise AssertionError()
        if not 0 <= pos[1] <= 1:
            raise AssertionError()
        pos = Point2((pos[0], pos[1]))
        self._debug_texts.append(DrawItemScreenText(text=text, color=color, start_point=pos, font_size=size))

    def debug_text_2d(
        self,
        text: str,
        pos: Union[Point2, Point3, tuple, list],
        color: Union[tuple, list, Point3] = None,
        size: int = 8,
    ):
        return self.debug_text_screen(text, pos, color, size)

    def debug_text_world(
        self, text: str, pos: Union[Unit, Point2, Point3], color: Union[tuple, list, Point3] = None, size: int = 8
    ):
        """ Draws a text at Point3 position in the game world. To grab a unit's 3d position, use unit.position3d
        Usually the Z value of a Point3 is between 8 and 14 (except for flying units). Use self.get_terrain_z_height()
        from bot_ai.py to get the Z value (height) of the terrain at a 2D position.
        """
        if isinstance(pos, Point2) and not isinstance(pos, Point3):  # a Point3 is also a Point2
            pos = Point3((pos.x, pos.y, 0))
        self._debug_texts.append(DrawItemWorldText(text=text, color=color, start_point=pos, font_size=size))

    def debug_text_3d(
        self, text: str, pos: Union[Unit, Point2, Point3], color: Union[tuple, list, Point3] = None, size: int = 8
    ):
        return self.debug_text_world(text, pos, color, size)

    def debug_line_out(
        self, p0: Union[Unit, Point2, Point3], p1: Union[Unit, Point2, Point3], color: Union[tuple, list, Point3] = None
    ):
        """ Draws a line from p0 to p1. """
        self._debug_lines.append(DrawItemLine(color=color, start_point=p0, end_point=p1))

    def debug_box_out(
        self,
        p_min: Union[Unit, Point2, Point3],
        p_max: Union[Unit, Point2, Point3],
        color: Union[tuple, list, Point3] = None,
    ):
        """ Draws a box with p_min and p_max as corners of the box. """
        self._debug_boxes.append(DrawItemBox(start_point=p_min, end_point=p_max, color=color))

    def debug_box2_out(
        self,
        pos: Union[Unit, Point2, Point3],
        half_vertex_length: float = 0.25,
        color: Union[tuple, list, Point3] = None,
    ):
        """ Draws a box center at a position 'pos',
        with box side lengths (vertices) of two times 'half_vertex_length'. """
        if isinstance(pos, Unit):
            pos = pos.position3d
        elif not isinstance(pos, Point3):
            pos = Point3((pos.x, pos.y, 0))
        p0 = pos + Point3((-half_vertex_length, -half_vertex_length, -half_vertex_length))
        p1 = pos + Point3((half_vertex_length, half_vertex_length, half_vertex_length))
        self._debug_boxes.append(DrawItemBox(start_point=p0, end_point=p1, color=color))

    def debug_sphere_out(
        self, p: Union[Unit, Point2, Point3], r: Union[int, float], color: Union[tuple, list, Point3] = None
    ):
        """ Draws a sphere at point p with radius r. """
        self._debug_spheres.append(DrawItemSphere(start_point=p, radius=r, color=color))

    async def send_debug(self):
        """ Sends the debug draw execution. This is run by main.py now automatically, if there is any items in the
        list. You do not need to run this manually any longer. Check examples/terran/ramp_wall.py for example
        drawing. Each draw request needs to be sent again in every single on_step iteration.
        """
        debug_hash = (
            sum(hash(item) for item in self._debug_texts),
            sum(hash(item) for item in self._debug_lines),
            sum(hash(item) for item in self._debug_boxes),
            sum(hash(item) for item in self._debug_spheres),
        )
        if debug_hash != (0, 0, 0, 0):
            if debug_hash != self._debug_hash_tuple_last_iteration:
                # Something has changed, either more or less is to be drawn, or a position of a drawing changed
                # (e.g. when drawing on a moving unit)
                self._debug_hash_tuple_last_iteration = debug_hash
                await self.execute(
                    debug=sc_pb.RequestDebug(
                        debug=[
                            debug_pb.DebugCommand(
                                draw=debug_pb.DebugDraw(
                                    text=[text.to_proto() for text in self._debug_texts] if self._debug_texts else None,
                                    lines=[line.to_proto() for line in self._debug_lines]
                                    if self._debug_lines
                                    else None,
                                    boxes=[box.to_proto() for box in self._debug_boxes] if self._debug_boxes else None,
                                    spheres=[sphere.to_proto() for sphere in self._debug_spheres]
                                    if self._debug_spheres
                                    else None,
                                )
                            )
                        ]
                    )
                )
            self._debug_draw_last_frame = True
            self._debug_texts.clear()
            self._debug_lines.clear()
            self._debug_boxes.clear()
            self._debug_spheres.clear()
        elif self._debug_draw_last_frame:
            # Clear drawing if we drew last frame but nothing to draw this frame
            self._debug_hash_tuple_last_iteration = (0, 0, 0, 0)
            await self.execute(
                debug=sc_pb.RequestDebug(
                    debug=[
                        debug_pb.DebugCommand(draw=debug_pb.DebugDraw(text=None, lines=None, boxes=None, spheres=None))
                    ]
                )
            )
            self._debug_draw_last_frame = False

    async def debug_leave(self):
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(end_game=debug_pb.DebugEndGame())]))

    async def debug_set_unit_value(self, unit_tags: Union[Iterable[int], Units, Unit], unit_value: int, value: float):
        """ Sets a "unit value" (Energy, Life or Shields) of the given units to the given value. Can't set the life
        of a unit to 0, use "debug_kill_unit" for that. Also can't set the life above the unit's maximum. The
        following example sets the health of all your workers to 1: await self.debug_set_unit_value(self.workers, 2,
        value=1) """
        if isinstance(unit_tags, Units):
            unit_tags = unit_tags.tags
        if isinstance(unit_tags, Unit):
            unit_tags = [unit_tags.tag]
        if not hasattr(unit_tags, "__iter__"):
            raise AssertionError(
                f"unit_tags argument needs to be an iterable (list, dict, set, Units),"
                f" given argument is {type(unit_tags).__name__}"
            )
        if not 1 <= unit_value <= 3:
            raise AssertionError(
                f"unit_value needs to be between 1 and 3 (1 for energy, 2 for life, 3 for shields),"
                f" given argument is {unit_value}"
            )
        if not all(tag > 0 for tag in unit_tags):
            raise AssertionError(f"Unit tags have invalid value: {unit_tags}")
        if not isinstance(value, (int, float)):
            raise AssertionError("Value needs to be of type int or float")
        if value < 0:
            raise AssertionError("Value can't be negative")
        await self.execute(
            debug=sc_pb.RequestDebug(
                debug=(
                    debug_pb.DebugCommand(
                        unit_value=debug_pb.DebugSetUnitValue(
                            unit_value=unit_value, value=float(value), unit_tag=unit_tag
                        )
                    )
                    for unit_tag in unit_tags
                )
            )
        )

    async def debug_hang(self, delay_in_seconds: float):
        """ Freezes the SC2 client. Not recommended to be used. """
        delay_in_ms = int(round(delay_in_seconds * 1000))
        await self.execute(
            debug=sc_pb.RequestDebug(
                debug=[debug_pb.DebugCommand(test_process=debug_pb.DebugTestProcess(test=1, delay_ms=delay_in_ms))]
            )
        )

    async def debug_show_map(self):
        """ Reveals the whole map for the bot. Using it a second time disables it again. """
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=1)]))

    async def debug_control_enemy(self):
        """ Allows control over enemy units and structures similar to team games control - does not allow the bot to
        spend the opponent's resources. Using it a second time disables it again. """
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=2)]))

    async def debug_food(self):
        """ Should disable food usage (does not seem to work?). Using it a second time disables it again.  """
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=3)]))

    async def debug_free(self):
        """ Units, structures and upgrades are free of mineral and gas cost. Using it a second time disables it
        again. """
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=4)]))

    async def debug_all_resources(self):
        """ Gives 5000 minerals and 5000 vespene to the bot. """
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=5)]))

    async def debug_god(self):
        """ Your units and structures no longer take any damage. Using it a second time disables it again. """
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=6)]))

    async def debug_minerals(self):
        """ Gives 5000 minerals to the bot. """
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=7)]))

    async def debug_gas(self):
        """ Gives 5000 vespene to the bot. This does not seem to be working. """
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=8)]))

    async def debug_cooldown(self):
        """ Disables cooldowns of unit abilities for the bot. Using it a second time disables it again. """
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=9)]))

    async def debug_tech_tree(self):
        """ Removes all tech requirements (e.g. can build a factory without having a barracks).
        Using it a second time disables it again. """
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=10)]))

    async def debug_upgrade(self):
        """ Researches all currently available upgrades. E.g. using it once unlocks combat shield, stimpack and 1-1.
         Using it a second time unlocks 2-2 and all other upgrades stay researched. """
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=11)]))

    async def debug_fast_build(self):
        """ Sets the build time of units and structures and upgrades to zero. Using it a second time disables it
        again. """
        await self.execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=12)]))

    async def quick_save(self):
        """ Saves the current game state to an in-memory bookmark."""
        await self.execute(quick_save=sc_pb.RequestQuickSave())

    async def quick_load(self):
        """ Loads the game state from the previously stored in-memory bookmark.
        Caution:
            - The SC2 Client will crash if the game wasn't quicksaved
            - The bot step iteration counter will not reset
            - self.state.game_loop will be set to zero after the quickload, and self.time is dependant on it """
        await self.execute(quick_load=sc_pb.RequestQuickLoad())


class DrawItem:
    @staticmethod
    def to_debug_point(point: Union[Unit, Point2, Point3]) -> common_pb.Point:
        """ Helper function for point conversion """
        if isinstance(point, Unit):
            point = point.position3d
        return common_pb.Point(x=point.x, y=point.y, z=getattr(point, "z", 0))

    @staticmethod
    def to_debug_color(color: Union[tuple, Point3]):
        """ Helper function for color conversion """
        if color is None:
            return debug_pb.Color(r=255, g=255, b=255)
        # Need to check if not of type Point3 because Point3 inherits from tuple
        if isinstance(color, (tuple, list)) and not isinstance(color, Point3) and len(color) == 3:
            return debug_pb.Color(r=color[0], g=color[1], b=color[2])
        # In case color is of type Point3
        r = getattr(color, "r", getattr(color, "x", 255))
        g = getattr(color, "g", getattr(color, "y", 255))
        b = getattr(color, "b", getattr(color, "z", 255))
        if max(r, g, b) <= 1:
            r *= 255
            g *= 255
            b *= 255

        return debug_pb.Color(r=int(r), g=int(g), b=int(b))


class DrawItemScreenText(DrawItem):
    def __init__(self, start_point: Point2 = None, color: Point3 = None, text: str = "", font_size: int = 8):
        self._start_point: Point2 = start_point
        self._color: Point3 = color
        self._text: str = text
        self._font_size: int = font_size

    def to_proto(self):
        return debug_pb.DebugText(
            color=self.to_debug_color(self._color),
            text=self._text,
            virtual_pos=self.to_debug_point(self._start_point),
            world_pos=None,
            size=self._font_size,
        )

    def __hash__(self):
        return hash((self._start_point, self._color, self._text, self._font_size))


class DrawItemWorldText(DrawItem):
    def __init__(self, start_point: Point3 = None, color: Point3 = None, text: str = "", font_size: int = 8):
        self._start_point: Point3 = start_point
        self._color: Point3 = color
        self._text: str = text
        self._font_size: int = font_size

    def to_proto(self):
        return debug_pb.DebugText(
            color=self.to_debug_color(self._color),
            text=self._text,
            virtual_pos=None,
            world_pos=self.to_debug_point(self._start_point),
            size=self._font_size,
        )

    def __hash__(self):
        return hash((self._start_point, self._text, self._font_size, self._color))


class DrawItemLine(DrawItem):
    def __init__(self, start_point: Point3 = None, end_point: Point3 = None, color: Point3 = None):
        self._start_point: Point3 = start_point
        self._end_point: Point3 = end_point
        self._color: Point3 = color

    def to_proto(self):
        return debug_pb.DebugLine(
            line=debug_pb.Line(p0=self.to_debug_point(self._start_point), p1=self.to_debug_point(self._end_point)),
            color=self.to_debug_color(self._color),
        )

    def __hash__(self):
        return hash((self._start_point, self._end_point, self._color))


class DrawItemBox(DrawItem):
    def __init__(self, start_point: Point3 = None, end_point: Point3 = None, color: Point3 = None):
        self._start_point: Point3 = start_point
        self._end_point: Point3 = end_point
        self._color: Point3 = color

    def to_proto(self):
        return debug_pb.DebugBox(
            min=self.to_debug_point(self._start_point),
            max=self.to_debug_point(self._end_point),
            color=self.to_debug_color(self._color),
        )

    def __hash__(self):
        return hash((self._start_point, self._end_point, self._color))


class DrawItemSphere(DrawItem):
    def __init__(self, start_point: Point3 = None, radius: float = None, color: Point3 = None):
        self._start_point: Point3 = start_point
        self._radius: float = radius
        self._color: Point3 = color

    def to_proto(self):
        return debug_pb.DebugSphere(
            p=self.to_debug_point(self._start_point), r=self._radius, color=self.to_debug_color(self._color)
        )

    def __hash__(self):
        return hash((self._start_point, self._radius, self._color))
