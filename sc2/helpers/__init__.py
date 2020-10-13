"""
Sets what files will be imported when 'from helpers import *' gets called
"""
from pathlib import Path

from .control_group import ControlGroup


def is_submodule(path):
    """ Check if the path is a submodule"""
    if path.is_file():
        return path.suffix == ".py" and path.stem != "__init__"
    if path.is_dir():
        return (path / "__init__.py").exists()
    return False


__all__ = [p.stem for p in Path(__file__).parent.iterdir() if is_submodule(p)]
