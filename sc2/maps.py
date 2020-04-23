"""
Open the map and return some info about it like the name
"""
import logging

from .paths import Paths

LOGGER = logging.getLogger(__name__)


def get(name=None):
    """ Get all available maps returns the one given as a parameter"""
    maps = []
    for map_directory in (p for p in Paths.MAPS.iterdir()):
        if map_directory.is_dir():
            for map_file in (p for p in map_directory.iterdir() if p.is_file()):
                if map_file.suffix == ".SC2Map":
                    maps.append(Map(map_file))
        elif map_directory.is_file():
            if map_directory.suffix == ".SC2Map":
                maps.append(Map(map_directory))

    if name is None:
        return maps

    for chart in maps:
        if chart.matches(name):
            return chart

    raise KeyError(f"Map '{name}' was not found. Please put the map file in \"/StarCraft II/Maps/\".")


class Map:
    """Gets some info about the selected map"""

    def __init__(self, path):
        self.path = path

        if self.path.is_absolute():
            try:
                self.relative_path = self.path.relative_to(Paths.MAPS)
            except ValueError:  # path not relative to basedir
                logging.warning(f"Using absolute path: {self.path}")
                self.relative_path = self.path
        else:
            self.relative_path = self.path

    @property
    def name(self):
        """Returns the name of the map"""
        return self.path.stem

    @property
    def data(self):
        """ not sure what it does"""
        with open(self.path, "rb") as data:
            return data.read()

    def matches(self, name):
        """ Check if the given name matches the path name"""
        return self.name.lower().replace(" ", "") == name.lower().replace(" ", "")

    def __repr__(self):
        """ Prints the given path"""
        return f"Map({self.path})"
