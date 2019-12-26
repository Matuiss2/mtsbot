import logging

from .paths import Paths

LOGGER = logging.getLogger(__name__)


def get(name=None):
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

    for m in maps:
        if m.matches(name):
            return m

    raise KeyError(f"Map '{name}' was not found. Please put the map file in \"/StarCraft II/Maps/\".")


class Map:
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
        return self.path.stem

    @property
    def data(self):
        with open(self.path, "rb") as f:
            return f.read()

    def matches(self, name):
        return self.name.lower().replace(" ", "") == name.lower().replace(" ", "")

    def __repr__(self):
        return f"Map({self.path})"
