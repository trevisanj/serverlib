__all__ = ["DBServerCommands"]

import serverlib as sl

class DBServerCommands(sl.ServerCommands):
    """Provides dbfile property"""
    @property
    def dbfile(self):
        return self.master.dbfile
