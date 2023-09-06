__all__ = ["WithCSVColumns"]

import a107


class WithCSVColumns:
    """Methods to manage database columns containing CSV."""

    async def _i_add_to_cell(self, id_, args, tablename, columnname):
        values = await self._i_get_cellvalues(id_, tablename, columnname)
        for arg in args:
            arg_ = arg.lower()
            if arg_ not in values: values.append(arg_)
        await self._i_set_cellvalues(id_, values, tablename, columnname)

    async def _i_del_from_cell(self, id_, args, tablename, columnname):
        values = await self._i_get_cellvalues(id_, tablename, columnname)
        for arg in args:
            try: values.remove(arg)
            except ValueError: pass
        await self._i_set_cellvalues(id_, values, tablename, columnname)

    async def _i_set_cellvalues(self, id_, values, tablename, columnname):
        db = self.master.dbfile
        as_str = a107.join_cell(values)
        db.execute(f"update {tablename} set {columnname}=? where id={id_}", (as_str,))
        db.commit()

    async def _i_get_cellvalues(self, id_, tablename, columnname):
        db = self.master.dbfile
        try:
            cell = db.get_scalar(f"select {columnname} from {tablename} where id={id_}")
        except a107.NoData:
            raise a107.NoData(f"Id {id_} does not exists in table '{tablename}'")
        if cell is None:
            cell = ""
        values = a107.split_cell(cell)
        return values
