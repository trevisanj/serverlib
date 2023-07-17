#!/usr/bin/env python
import serverlib as sl, a107, time
__doc__ = """Achievemtns - DBServer demonstration."""


class AchievementsCommands(sl.DBServerCommands):

    @sl.is_command
    async def achieve(self, *args):
        self.dbfile.execute("insert into achievement (whenthis, description) values (?, ?)",
                            (time.time(), " ".join(args),))
        self.dbfile.commit()

    @sl.is_command
    async def list(self):
        return [dict(row) for row in self.dbfile.execute("select * from achievement")]

class AchievementsDB(a107.FileSQLite):
    def _do_create_database(self):
        conn = self.conn
        conn.execute("create table achievement (id integer primary key,"
                     "whenthis datetime not null,"
                     "description text not null"
                     ")")
        self.commit()


if __name__ == "__main__":
    cfg = sl.DBServerConfig(port=6668,
                            flag_log_console=True,
                            appname="achievements",
                            datadir=".",
                            description=__doc__)

    server = sl.DBServer(cfg,
                         cmd=AchievementsCommands(),
                         fileclass=AchievementsDB)
    sl.cli_server(server)
