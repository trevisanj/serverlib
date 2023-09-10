__all__ = ["WithConsole"]

import os, a107
from . import _misc


class WithConsole:
    """Implements history and shelf for Console and Client classes."""

    @property
    def historypath(self):
        """Returns the path to the history file."""
        return self.filepath("console", ".history")

    @property
    def shelfpath(self):
        """Returns the path to the shelf file."""
        return self.filepath("console", "shelf")

    @property
    def fav(self):
        return self.shelf.get("fav", [])

    @fav.setter
    def fav(self, value):
        self.shelf["fav"] = value

    def __init__(self):
        path_ = self.shelfpath
        dir_, _ = os.path.split(path_)
        if a107.ensure_path(dir_):
            self.logger.info(f"Created directory '{dir_}'")

        self.shelf = _misc.ConsoleShelf(self.shelfpath)

