"""
Not sure what this file does
changed last: 28/12/2019
"""
from pathlib import Path

from .control_group import ControlGroup


def is_submodule(path):
    if path.is_file():
        return path.suffix == ".py" and path.stem != "__init__"
    if path.is_dir():
        return (path / "__init__.py").exists()
    return False


__all__ = [p.stem for p in Path(__file__).parent.iterdir() if is_submodule(p)]
