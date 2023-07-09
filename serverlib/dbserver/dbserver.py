__all__ = ["DBServer"]

import serverlib as sl, shelve

class DBServer(sl.Server):
    """SQLite database server with shelf ("shelve") option

    Args:
        fileclass: some MySQLite descendant class, or None (SQLite database is optional)
        flag_shelf: whether of not the server will implement "shelve" capability (if yes, the server will provide
                    commands through a sacca.ServerCommands_Shelf)
    """
    def __init__(self, *args, fileclass=None, flag_shelf=False, **kwargs):
        sl.Server.__init__(self, *args, **kwargs)

        if not isinstance(self.cfg, sl.DBServerConfig):
            raise TypeError(f"cfg must be a serverlib.DBServerConfig, not a {self.cfg.__class__.__name__}")

        self.dbfile = None
        if fileclass:
            self.dbfile = self._append_closer(fileclass(self.cfg.dbpath, master=self))
        if flag_shelf:
            self.shelf = self._append_closer(shelve.open(self.cfg.shelfpath))
            self._attach_cmd(sl.ServerCommands_Shelf(self.shelf))
        if self.dbfile:
            self._attach_cmd(sl.DBServerCommands_FileSQLite())

    async def _on_initialize(self):
        if self.dbfile:
            self.dbfile.create_database()

    async def _on_close(self):
        if self.dbfile:
            self.dbfile.commit()
