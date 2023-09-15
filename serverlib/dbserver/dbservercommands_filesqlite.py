__all__ = ["DBServerCommands_FileSQLite"]


import serverlib as sl, a107
from serverlib import is_command
from .dbservercommands import *


class DBServerCommands_FileSQLite(DBServerCommands):
    """"Low-level" access to FileSQLite object."""

    @is_command
    async def s_commit(self):
        """Commits the current transaction."""
        self.dbfile.commit()

    @is_command
    async def s_execute(self, statement, bindings=(), rowformat="dict", flag_commit=False):
        """Executes SQLite statement.

        Args:
            statement: SQLite statement
            bindings: statement bindings
            rowformat: "row" (default) / "list" (converts to list of lists) / "dict" (converts to list of dicts)
            flag_commit: whether to commit after executing statement

        Returns:
            list of rows
        """
        cursor = self.dbfile.execute(statement, bindings)
        if flag_commit:
            self.dbfile.commit()
        return _format_cursor(cursor, rowformat)

    @is_command
    async def s_executemany(self, statement, bindings=(), flag_commit=False):
        """Executes SQLite statement repeatedly for each row in bindings.

        Args:
            statement: SQLite statement
            bindings: statement bindings
            flag_commit: whether to commit after executing statements
        Returns:
            list of rows
        """
        self.dbfile.executemany(statement, bindings)
        if flag_commit: self.dbfile.commit()

    @is_command
    async def s_get_scalar(self, *args, **kwargs):
        """Executes statement that presumably fetches one row containing one column."""
        return self.dbfile.get_scalar(*args, **kwargs)

    @is_command
    async def s_get_singlecolumn(self, *args, **kwargs):
        """Executes statement that presumably feches one column per row."""
        return self.dbfile.get_singlecolumn(*args, **kwargs)

    @is_command
    async def s_get_singlerow(self, statement, bindings=(), rowformat="dict"):
        """Executes statement that presumably feches one row only. **Does** raise if rowcount != 1"""
        _ret = self.dbfile.execute(statement, bindings).fetchall()
        if len(_ret) != 1:
            raise ValueError(f"Statement must produce number of rows ==1, not {len(_ret)}")
        ret = _format_cursor(_ret, rowformat)[0]
        return ret

    @is_command
    async def s_describe(self, tablename, rowformat="dict"):
        """Making up for the lack of SQL "describe" command."""
        return _format_cursor(self.dbfile.describe(tablename), rowformat)

    @is_command
    async def s_show_tables(self, rowformat="dict"):
        """Making up for the lack of SQL "show tables" statement."""
        return _format_cursor(self.dbfile.show_tables(), rowformat)

    @is_command
    async def s_create_database(self, flag_overwrite=False):
        """Creates database if it does not exist or if forced overwriting. **Careful**"""
        flag_overwrite = a107.to_bool(flag_overwrite)
        self.dbfile.create_database(flag_overwrite=flag_overwrite)



def _format_cursor(cursor, rowformat):
    if rowformat == "list":
        ret = [list(row) for row in cursor]
    elif rowformat == "dict":
        ret = [dict(row) for row in cursor]
    else:
        raise ValueError(f"Invalid row format: {rowformat}")
    return ret
