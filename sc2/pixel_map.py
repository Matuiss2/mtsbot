"""
Groups all info about the map(it's different from game_info that gets info about the map TERRAIN)
"""
from typing import Callable, FrozenSet, List, Set

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from .position import Point2


class PixelMap:
    """ Groups all info about the map"""

    def __init__(self, proto, in_bits: bool = False, mirrored: bool = False):
        """
        :param proto:
        :param in_bits:
        :param mirrored:
        """
        self.proto = proto
        self._in_bits: bool = in_bits
        self._mirrored: bool = mirrored

        if self.width * self.height != (8 if in_bits else 1) * len(self.proto.data):
            raise AssertionError(f"{self.width * self.height} {(8 if in_bits else 1)*len(self.proto.data)}")
        buffer_data = np.frombuffer(self.proto.data, dtype=np.uint8)
        if in_bits:
            buffer_data = np.unpackbits(buffer_data)
        self.data_numpy = buffer_data.reshape(self.proto.size.y, self.proto.size.x)
        if mirrored:
            self.data_numpy = np.flipud(self.data_numpy)

    @property
    def width(self):
        """Return the map width in pixels"""
        return self.proto.size.x

    @property
    def height(self):
        """Return the map height in pixels"""
        return self.proto.size.y

    @property
    def bits_per_pixel(self):
        """Return the amount of bits in 1 pixel"""
        return self.proto.bits_per_pixel

    @property
    def bytes_per_pixel(self):
        """Return the amount of bytes in 1 pixel"""
        return self.proto.bits_per_pixel // 8

    def __getitem__(self, pos):
        """ Example usage: is_passable = self._game_info.pathway_grid[Point2((20, 20))] != 0 """
        if not 0 <= pos[0] < self.width:
            raise AssertionError(f"x is {pos[0]}, self.width is {self.width}")
        if not 0 <= pos[1] < self.height:
            raise AssertionError(f"y is {pos[1]}, self.height is {self.height}")
        return int(self.data_numpy[pos[1], pos[0]])

    def __setitem__(self, pos, value):
        """ Example usage: self._game_info.pathway_grid[Point2((20, 20))] = 255 """
        if not 0 <= pos[0] < self.width:
            raise AssertionError(f"x is {pos[0]}, self.width is {self.width}")
        if not 0 <= pos[1] < self.height:
            raise AssertionError(f"y is {pos[1]}, self.height is {self.height}")
        if not 0 <= value <= 254 * self._in_bits + 1:
            raise AssertionError(f"value is {value}, it should be between 0 and {254 * self._in_bits + 1}")
        if not isinstance(value, int):
            raise AssertionError(f"value is of type {type(value)}, it should be an integer")
        self.data_numpy[pos[1], pos[0]] = value

    def is_set(self, position):
        """ Not sure what it does"""
        return bool(self[position])

    def is_empty(self, position):
        """ Not sure what it does"""
        return not self.is_set(position)

    def copy(self):
        """ It makes a copy of the PixelMap"""
        return PixelMap(self.proto, in_bits=self._in_bits, mirrored=self._mirrored)

    def flood_fill(self, start_point: Point2, pred: Callable[[int], bool]) -> Set[Point2]:
        """ Not sure what it does"""
        nodes: Set[Point2] = set()
        queue: List[Point2] = [start_point]

        while queue:
            x, y = queue.pop()

            if not (0 <= x < self.width and 0 <= y < self.height):
                continue

            if Point2((x, y)) in nodes:
                continue

            if pred(self[x, y]):
                nodes.add(Point2((x, y)))
                queue += [Point2((x + a, y + b)) for a in [-1, 0, 1] for b in [-1, 0, 1] if a or b]
        return nodes

    def flood_fill_all(self, pred: Callable[[int], bool]) -> Set[FrozenSet[Point2]]:
        """ Not sure what it does"""
        groups: Set[FrozenSet[Point2]] = set()

        for x in range(self.width):
            for y in range(self.height):
                if any((x, y) in g for g in groups):
                    continue

                if pred(self[x, y]):
                    groups.add(frozenset(self.flood_fill(Point2((x, y)), pred)))

        return groups

    def print(self, wide=False):
        """ Not sure what it does"""
        for y in range(self.height):
            for x in range(self.width):
                print("#" if self.is_set((x, y)) else " ", end=(" " if wide else ""))
            print("")

    def save_image(self, filename):
        """ Save a print-screen of the map and whats in it, with the given name """
        data = [(0, 0, self[x, y]) for y in range(self.height) for x in range(self.width)]

        img = Image.new("RGB", (self.width, self.height))
        img.putdata(data)
        img.save(filename)

    def plot(self):
        """ Plot the flipped image data"""
        plt.imshow(self.data_numpy, origin="lower")
        plt.show()
