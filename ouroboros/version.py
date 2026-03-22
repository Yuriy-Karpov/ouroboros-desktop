from pathlib import Path as _Path
from functools import cache


@cache
def get_version():
    root = _Path(__file__).resolve().parent

    try:
        version = (root.parent / 'VERSION').read_text(encoding='utf-8').strip()
    except FileNotFoundError as _:
        # Already installed
        from importlib.metadata import version
        version = version("ouroboros")

    return version
