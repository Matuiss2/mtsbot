"""
Groups useful data from the map
"""
from __future__ import annotations

from collections import deque
from typing import Deque, List, Set, Tuple

import numpy as np

from .cache import property_immutable_cache, property_mutable_cache
from .pixel_map import PixelMap
from .player import Player
from .position import Point2, Rect, Size


class Ramp:
    """ Groups useful data from the ramps"""

    def __init__(self, points: Set[Point2], game_info: GameInfo):
        """
        :param points:
        :param game_info:
        """
        self._points: Set[Point2] = points
        self.__game_info = game_info
        self.x_offset = 0.5
        self.y_offset = 0.5

    @property_immutable_cache
    def _height_map(self):
        return self.__game_info.terrain_height

    @property_immutable_cache
    def _placement_grid(self):
        return self.__game_info.placement_grid

    @property_immutable_cache
    def size(self) -> int:
        """ returns the ramp size"""
        return len(self._points)

    def height_at(self, position: Point2) -> int:
        """ returns the ramp height at given position"""
        return self.__game_info.terrain_height[position]

    @property_mutable_cache
    def points(self) -> Set[Point2]:
        """Returns all points of a ramp """
        return self._points.copy()

    @property_mutable_cache
    def upper(self) -> Set[Point2]:
        """ Returns the upper points of a ramp. """
        current_max = -10000
        result = set()
        for point in self._points:
            height = self.height_at(point)
            if height > current_max:
                current_max = height
                result = {point}
            elif height == current_max:
                result.add(point)
        return result

    @property_mutable_cache
    def upper2_for_ramp_wall(self) -> Set[Point2]:
        """ Returns the 2 upper ramp points of the main base ramp required for the supply depot and barracks
        placement properties used in this file. """
        if len(self.upper) > 5:
            return set()

        upper2 = sorted(list(self.upper), key=lambda x: x.distance_to_point2(self.bottom_center), reverse=True)
        while len(upper2) > 2:
            upper2.pop()
        return set(upper2)

    @property_immutable_cache
    def top_center(self) -> Point2:
        """ Returns the center point of the upper points in a ramp. """
        upper = set(self.upper)
        length = len(upper)
        pos = Point2((sum(p.x for p in upper) / length, sum(p.y for p in upper) / length))
        return pos

    @property_mutable_cache
    def lower(self) -> Set[Point2]:
        """ Returns the lower points of a ramp. """
        current_min = 10000
        result = set()
        for point in self._points:
            height = self.height_at(point)
            if height < current_min:
                current_min = height
                result = {point}
            elif height == current_min:
                result.add(point)
        return result

    @property_immutable_cache
    def bottom_center(self) -> Point2:
        """ Returns the center point of the lower points in a ramp. """
        lower = set(self.lower)
        length = len(lower)
        pos = Point2((sum(p.x for p in lower) / length, sum(p.y for p in lower) / length))
        return pos


class GameInfo:
    """ Groups the map terrain, path, destructible etc, data """

    def __init__(self, proto):
        self.proto = proto
        self.players: List[Player] = [Player.from_proto(p) for p in self.proto.player_info]
        self.map_name: str = self.proto.map_name
        self.local_map_path: str = self.proto.local_map_path
        self.map_size: Size = Size.from_proto(self.proto.start_raw.map_size)

        # self.pathway_grid[position]: if 0, position is not passable, if 1, position is passable
        self.pathway_grid: PixelMap = PixelMap(self.proto.start_raw.pathing_grid, in_bits=True, mirrored=False)
        # self.terrain_height[position]: returns the height in range of 0 to 255 at that position
        self.terrain_height: PixelMap = PixelMap(self.proto.start_raw.terrain_height, mirrored=False)
        # self.placement_grid[position]: if 0, position is not buildable, if 1, position is passable
        self.placement_grid: PixelMap = PixelMap(self.proto.start_raw.placement_grid, in_bits=True, mirrored=False)
        self.playable_area = Rect.from_proto(self.proto.start_raw.playable_area)
        self.map_center = self.playable_area.center
        self.map_ramps: List[Ramp] = None
        self.vision_blockers: Set[Point2] = None
        self.player_races = {p.player_id: p.race_actual or p.race_requested for p in self.proto.player_info}
        self.start_locations: List[Point2] = [Point2.from_proto(sl) for sl in self.proto.start_raw.start_locations]
        self.player_start_location: Point2 = None

    def find_ramps_and_vision_blockers(self) -> Tuple[List[Ramp], Set[Point2]]:
        """ Calculate points that are passable but not buildable.
        Then divide them into ramp points if not all points around the points are equal height
        and into vision blockers if they are. """

        def equal_height_around(tile):
            """Check if the sliced tiles are same weight"""
            sliced = self.terrain_height.data_numpy[tile[1] - 1 : tile[1] + 2, tile[0] - 1 : tile[0] + 2]
            return len(np.unique(sliced)) == 1

        map_area = self.playable_area
        points = [
            Point2((a, b))
            for (b, a), value in np.ndenumerate(self.pathway_grid.data_numpy)
            if value == 1
            and map_area.x <= a < map_area.x + map_area.width
            and map_area.y <= b < map_area.y + map_area.height
            and not self.placement_grid[(a, b)]
        ]
        ramp_points = [point for point in points if not equal_height_around(point)]
        vision_blockers = set(point for point in points if equal_height_around(point))
        ramps = [Ramp(group, self) for group in self._find_groups(ramp_points)]
        return ramps, vision_blockers

    def _find_groups(self, points: Set[Point2], minimum_points_per_group: int = 8):
        """
        From a set of points, this function will try to group points together by
        painting clusters of points in a rectangular map using flood fill algorithm.
        Returns groups of points as list, like [{p1, p2, p3}, {p4, p5, p6, p7, p8}]
        """
        not_colored_yet = -1
        map_width = self.pathway_grid.width
        map_height = self.pathway_grid.height
        current_color: int = not_colored_yet
        picture: List[List[int]] = [[-2 for _ in range(map_width)] for _ in range(map_height)]

        def paint(pnt: Point2) -> None:
            picture[pnt.y][pnt.x] = current_color

        nearby = [(a, b) for a in [-1, 0, 1] for b in [-1, 0, 1] if a or b]

        remaining: Set[Point2] = set(points)
        for point in remaining:
            paint(point)
        current_color = 1
        queue: Deque[Point2] = deque()
        while remaining:
            current_group: Set[Point2] = set()
            if not queue:
                start = remaining.pop()
                paint(start)
                queue.append(start)
                current_group.add(start)
            while queue:
                base: Point2 = queue.popleft()
                for offset in nearby:
                    point_x, point_y = base.x + offset[0], base.y + offset[1]
                    if not (0 <= point_x < map_width and 0 <= point_y < map_height):
                        continue
                    if picture[point_y][point_x] != not_colored_yet:
                        continue
                    point: Point2 = Point2((point_x, point_y))
                    remaining.discard(point)
                    paint(point)
                    queue.append(point)
                    current_group.add(point)
            if len(current_group) >= minimum_points_per_group:
                yield current_group
