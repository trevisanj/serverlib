"""This module stores part of a "create table" statement corresponding to the "task-related" of said statement."""

__all_ = ["taskpart_table", "taskpart_asstr", "taskpart_indexes", "BasicTaskDB"]

import a107


taskpart_table = {
"id": "integer primary key",
"agentname": "text not null",
"command": "text not null",
"time_of_day": "text",
"interval": "integer",
"lasttime": "real",
"nexttime": "real not null default 0",
"state": "text not null default 'idle'",
"result": "text not null default ''",
"lasterror": "text",
}


def taskpart_asstr(flag_final_comma=False):
    return ", ".join(f"{k} {v}" for k, v in taskpart_table.items())+(", " if flag_final_comma else "")


taskpart_indexes = [
    "create index task_nexttime on task (nexttime)",
    "create index task_agentname on task (agentname)",
]


class BasicTaskDB(a107.FileSQLite):
    """Minimum tasks database, also demonstrates how to create one."""

    def _do_create_database(self):
        conn = self.conn; e = conn.execute

        # TASKS ·▫·▯·□·▯·▫▯▫·▫·▯·□·▯·▫▯▫·▫·▯·□·▯·▫▯▫·▫·▯·□·▯·▫▯▫·▫·▯·□·▯·▫▯▫·▫·▯·□·▯·▫▯▫·▫·▯·□·▯·▫▯▫·▫·▯·□·▯·▫▯▫·▫·▯·□·▯
        e("create table task (" + taskpart_asstr() + ")")

        for sql in taskpart_indexes:
            e(sql)

