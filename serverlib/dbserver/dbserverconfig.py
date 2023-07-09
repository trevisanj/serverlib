__all__ = ["DBServerConfig"]

import serverlib as sl

class DBServerConfig(sl.ServerConfig):
    """Base class to be used as configuration for DBServer's"""
    @property
    def dbpath(self):
        return self._get_dbpath()
    @property
    def shelfpath(self):
        return self._get_shelfpath()

    def _get_dbpath(self):
        """Method to obtain the path to the .sqlite file (overwrittable)."""
        return self.filepath(".sqlite")

    def _get_shelfpath(self):
        """Method to obtain the path to the shelf file (overwrittable)."""
        return self.filepath("shelf")
