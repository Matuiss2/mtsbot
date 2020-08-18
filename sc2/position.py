"""
Everything about the Pointlike(coordinates) objects and their manipulation are here
"""
from __future__ import annotations

import itertools
import math
import random
from typing import TYPE_CHECKING, Iterable, List, Set, Tuple, Union

if TYPE_CHECKING:
    from .unit import Unit
    from .units import Units

EPSILON = 10 ** -8


def _sign(num):
    return math.copysign(1, num)


class Pointlike(tuple):
    """ Mother class for points it houses the shared functions"""

    @property
    def position(self) -> Pointlike:
        """ It returns the position of self"""
        return self

    def distance_to(self, target: Union[Unit, Point2]) -> float:
        """Calculate a single distance from a position or unit to another position or unit

        :param target: """
        position_x, position_y = target.position
        return math.hypot(self[0] - position_x, self[1] - position_y)

    def distance_to_point2(self, target_position: Union[Point2, Tuple[float, float]]) -> Union[int, float]:
        """ Same as the function above, but should be a bit faster because of the dropped asserts
        and conversion.

        :param target_position: """
        return math.hypot(self[0] - target_position[0], self[1] - target_position[1])

    def _distance_squared(self, point: Point2) -> Union[int, float]:
        """ Function used to not take the square root as the distances will stay proportionally the same.
        This is to speed up the sorting process.

        :param point: """
        return (self[0] - point[0]) ** 2 + (self[1] - point[1]) ** 2

    def is_closer_than(self, distance: Union[int, float], target: Union[Unit, Point2]) -> bool:
        """ Check if another position (or unit) is closer than the given distance.

        :param distance:
        :param target: """
        target = target.position
        return self.distance_to_point2(target) < distance

    def is_further_than(self, distance: Union[int, float], target: Union[Unit, Point2]) -> bool:
        """ Check if another position (or unit) is further than the given distance.

        :param distance:
        :param target: """
        target = target.position
        return self.distance_to_point2(target) > distance

    def sort_by_distance(self, positions: Union[Units, Iterable[Point2]]) -> List[Point2]:
        """ This returns the target points sorted as list.
        You should not pass a set or dict since those are not sortable.
        If you want to sort your units towards a position, use 'units.sorted_by_distance_to(position)' instead.

        :param positions: """
        return sorted(positions, key=lambda p: self.distance_to_point2(p.position))

    def closest(self, positions: Union[Units, Iterable[Point2]]) -> Union[Unit, Point2]:
        """ This function assumes the 2d distance is meant

        :param positions: """
        if not positions:
            raise AssertionError(f"ps is empty")
        return min(positions, key=self.distance_to)

    def distance_to_closest(self, positions: Union[Units, Iterable[Point2]]) -> Union[int, float]:
        """ This function assumes the 2d distance is meant
        :param positions: """
        if not positions:
            raise AssertionError(f"ps is empty")
        closest_distance = math.inf
        for pnt in positions:
            pnt = pnt.position
            distance = self.distance_to(pnt)
            if distance <= closest_distance:
                closest_distance = distance
        return closest_distance

    def furthest(self, positions: Union[Units, Iterable[Point2]]) -> Union[Unit, Pointlike]:
        """ This function assumes the 2d distance is meant

        :param positions: Units object, or iterable of Unit or Point2 """
        if not positions:
            raise AssertionError(f"ps is empty")
        return max(positions, key=self.distance_to)

    def distance_to_furthest(self, positions: Union[Units, Iterable[Point2]]) -> Union[int, float]:
        """ This function assumes the 2d distance is meant

        :param positions: """
        if not positions:
            raise AssertionError(f"ps is empty")
        furthest_distance = -math.inf
        for position in positions:
            position = position.position
            distance = self.distance_to(position)
            if distance >= furthest_distance:
                furthest_distance = distance
        return furthest_distance

    def offset(self, point) -> Pointlike:
        """

        :param point:
        """
        return self.__class__(a + b for a, b in itertools.zip_longest(self, point[: len(self)], fillvalue=0))

    def unit_axes_towards(self, point):
        """

        :param point:
        """
        return self.__class__(_sign(b - a) for a, b in itertools.zip_longest(self, point[: len(self)], fillvalue=0))

    def towards(
        self, target: Union[Unit, Pointlike], distance: Union[int, float] = 1, limit: bool = False
    ) -> Pointlike:
        """

        :param target:
        :param distance:
        :param limit:
        """
        target = target.position
        if self == target:
            return self
        distance_to_target = self.distance_to(target)
        if limit:
            distance = min(distance_to_target, distance)
        return self.__class__(
            a + (b - a) / distance_to_target * distance
            for a, b in itertools.zip_longest(self, target[: len(self)], fillvalue=0)
        )

    @property
    def to2(self) -> Point2:
        """ Convert the point to point2 and returns it"""
        return Point2(self[:2])

    def __eq__(self, other):
        return all(abs(a - b) <= EPSILON for a, b in itertools.zip_longest(self, other.position, fillvalue=0))

    def __hash__(self):
        return hash(tuple(self))


class Point2(Pointlike):
    """ Extends Pointlike specifies it to Point2(its a tuple with the coordinates) """

    @classmethod
    def from_proto(cls, data) -> Point2:
        """ Get necessary info from sc2 protocol"""
        return cls((data.x, data.y))

    @property
    def rounded(self) -> Point2:
        """ Rounds the x and y coordinates down"""
        return Point2((math.floor(self[0]), math.floor(self[1])))

    @property
    def length(self) -> float:
        """ This property exists in case Point2 is used as a vector. """
        return math.hypot(self[0], self[1])

    @property
    def normalized(self) -> Point2:
        """ This property exists in case Point2 is used as a vector. """
        length = self.length
        if not length:
            raise AssertionError()
        return self.__class__((self[0] / length, self[1] / length))

    @property
    def x(self) -> Union[int, float]:
        """ Returns the first element of the Point2 tuple"""
        return self[0]

    @property
    def y(self) -> Union[int, float]:
        """ Returns the second element of the Point2 tuple"""
        return self[1]

    @property
    def to3(self):
        """ Convert the point to point3 and returns it"""
        return Point3((*self, 0))

    def offset(self, off):
        """ Returns the offset point(by the amount in the parameter)"""
        return Point2((self[0] + off[0], self[1] + off[1]))

    def random_on_distance(self, distance):
        """ Returns a point with random direction from it at the given distance """
        if isinstance(distance, (tuple, list)):  # interval
            distance = distance[0] + random.SystemRandom() * (distance[1] - distance[0])

        if distance <= 0:
            raise AssertionError("Distance is not greater than 0")
        angle = random.SystemRandom() * 2 * math.pi

        cosine, sine = math.cos(angle), math.sin(angle)
        return Point2((self.x + cosine * distance, self.y + sine * distance))

    def towards_with_random_angle(
        self,
        target: Union[Point2, Point3],
        distance: Union[int, float] = 1,
        max_difference: Union[int, float] = (math.pi / 4),
    ) -> Point2:
        """ Not sure what it does"""
        tan_x, tan_y = self.to2.towards(target.to2, 1)
        angle = math.atan2(tan_y - self.y, tan_x - self.x)
        angle = (angle - max_difference) + max_difference * 2 * random.SystemRandom()
        return Point2((self.x + math.cos(angle) * distance, self.y + math.sin(angle) * distance))

    def circle_intersection(self, center: Point2, radius: Union[int, float]) -> Set[Point2]:
        """ self is point1, position is point2, radius is the radius for circles originating in both points
        Used in ramp finding

        :param center:
        :param radius: """
        if self == center:
            raise AssertionError(f"self is equal to position")
        distance_between_points = self.distance_to(center)
        if radius < distance_between_points / 2:
            raise AssertionError()
        remaining_distance_from_center = (radius ** 2 - (distance_between_points / 2) ** 2) ** 0.5
        offset_to_center = Point2(((center.x - self.x) / 2, (center.y - self.y) / 2))
        center = self.offset(offset_to_center)

        vector_stretch_factor = remaining_distance_from_center / (distance_between_points / 2)
        vector = offset_to_center
        offset_to_center_stretched = Point2((vector.x * vector_stretch_factor, vector.y * vector_stretch_factor))

        vector_rotated1 = Point2((offset_to_center_stretched.y, -offset_to_center_stretched.x))
        vector_rotated2 = Point2((-offset_to_center_stretched.y, offset_to_center_stretched.x))
        intersect1 = center.offset(vector_rotated1)
        intersect2 = center.offset(vector_rotated2)
        return {intersect1, intersect2}

    @property
    def neighbors4(self) -> set:
        """ Get the positions N, E, S, and W around the point"""
        return {
            Point2((self.x - 1, self.y)),
            Point2((self.x + 1, self.y)),
            Point2((self.x, self.y - 1)),
            Point2((self.x, self.y + 1)),
        }

    @property
    def neighbors8(self) -> set:
        """ Get the positions N, E, S, W, NE, SE, SW, and NW around the point"""
        return self.neighbors4 | {
            Point2((self.x - 1, self.y - 1)),
            Point2((self.x - 1, self.y + 1)),
            Point2((self.x + 1, self.y - 1)),
            Point2((self.x + 1, self.y + 1)),
        }

    def negative_offset(self, other: Point2) -> Point2:
        """ Returns the negative offset point(by the amount in the parameter)"""
        return self.__class__((self.x - other.x, self.y - other.y))

    def __add__(self, other: Point2) -> Point2:
        return self.offset(other)

    def __sub__(self, other: Point2) -> Point2:
        return self.negative_offset(other)

    def __neg__(self) -> Point2:
        return self.__class__(-a for a in self)

    def __abs__(self) -> Union[int, float]:
        return math.hypot(self.x, self.y)

    def __bool__(self) -> bool:
        return bool(self.x) or bool(self.y)

    def __mul__(self, other: Union[int, float, Point2]) -> Point2:
        try:
            return self.__class__((self.x * other.x, self.y * other.y))
        except AttributeError:
            return self.__class__((self.x * other, self.y * other))

    def __rmul__(self, other: Union[int, float, Point2]) -> Point2:
        return self.__mul__(other)

    def __truediv__(self, other: Union[int, float, Point2]) -> Point2:
        if isinstance(other, self.__class__):
            return self.__class__((self.x / other.x, self.y / other.y))
        return self.__class__((self.x / other, self.y / other))

    def is_same_as(self, other: Point2, dist=0.001) -> bool:
        """ Check if the point(self) and point(other) are in the same place"""
        return self.distance_to_point2(other) <= dist

    def direction_vector(self, other: Point2) -> Point2:
        """ Converts a vector to a direction that can face vertically, horizontally or diagonal or be zero,
        e.g. (0, 0), (1, -1), (1, 0) """
        return self.__class__((_sign(other.x - self.x), _sign(other.y - self.y)))

    def manhattan_distance(self, other: Point2) -> Union[int, float]:
        """
        :param other:
        """
        return abs(other.x - self.x) + abs(other.y - self.y)

    @staticmethod
    def center(units_or_points: Iterable[Point2]) -> Point2:
        """ Returns the central position for points in list

        :param units_or_points:"""
        sum_of_points = Point2((0, 0))
        for unit_or_point in units_or_points:
            sum_of_points += unit_or_point
        return sum_of_points / len(units_or_points)


class Point3(Point2):
    """ Extends Point specifies it to Point3 its the same but includes the height"""

    @classmethod
    def from_proto(cls, data):
        """ Get necessary info from sc2 protocol"""
        return cls((data.x, data.y, data.z))

    @property
    def rounded(self) -> Point3:
        """ Rounds the x, y, z coordinates down"""
        return Point3((math.floor(self[0]), math.floor(self[1]), math.floor(self[2])))

    @property
    def z(self) -> Union[int, float]:
        """ Returns the height(z coordinate) of the self point"""
        return self[2]

    @property
    def to3(self) -> Point3:
        """ Convert the point to point3 and returns it"""
        return Point3(self)

    def __add__(self, other: Union[Point2, Point3]) -> Point3:
        if not isinstance(other, Point3) and isinstance(other, Point2):
            return Point3((self.x + other.x, self.y + other.y, self.z))
        return Point3((self.x + other.x, self.y + other.y, self.z + other.z))


class Size(Point2):
    """ Extends the point2 class"""

    @property
    def width(self) -> Union[int, float]:
        """ Returns the x coordinate of the object"""
        return self[0]

    @property
    def height(self) -> Union[int, float]:
        """ Returns the y coordinate of the object"""
        return self[1]


class Rect(tuple):
    """ Extends tuple specifies it to Rectangles it behaves like the pointlike, its used to get the playable area"""

    @classmethod
    def from_proto(cls, data):
        """ Get necessary info from sc2 protocol"""
        if data.p0.x >= data.p1.x and data.p0.y >= data.p1.y:
            raise AssertionError()
        return cls((data.p0.x, data.p0.y, data.p1.x - data.p0.x, data.p1.y - data.p0.y))

    @property
    def x(self) -> Union[int, float]:
        """ Returns the x coordinate"""
        return self[0]

    @property
    def y(self) -> Union[int, float]:
        """ Returns the y coordinate"""
        return self[1]

    @property
    def width(self) -> Union[int, float]:
        """ Returns the width of the rectangle"""
        return self[2]

    @property
    def height(self) -> Union[int, float]:
        """ Returns the height of the rectangle"""
        return self[3]

    @property
    def size(self) -> Size:
        """ Returns the width and the height of the rectangle"""
        return Size((self[2], self[3]))

    @property
    def center(self) -> Point2:
        """ Returns the center of the rectangle"""
        return Point2((self.x + self.width / 2, self.y + self.height / 2))

    def offset(self, point):
        """ Returns the offset(off by the point given) of the rectangle"""
        return self.__class__((self[0] + point[0], self[1] + point[1], self[2], self[3]))
