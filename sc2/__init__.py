"""
Not sure what this file does
"""

import logging
import sys
from pathlib import Path

from . import maps


def is_submodule(path):
    """ Check if the path is a submodule"""
    if path.is_file():
        return path.suffix == ".py" and path.stem != "__init__"
    if path.is_dir():
        return bool(path / "__init__.py")
    return False


__all__ = [p.stem for p in Path(__file__).parent.iterdir() if is_submodule(p)]


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
LOGGER = logging.getLogger(__name__)
