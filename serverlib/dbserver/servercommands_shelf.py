import serverlib as sl, a107

__all__ = ["ServerCommands_Shelf"]

class ServerCommands_Shelf(sl.ServerCommands):
    def __init__(self, shelf):
        super().__init__()
        self.shelf = shelf

    # ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐
    # ┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──
    # OVERRIDE

    async def _on_initialize(self):
        pass

    # ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐
    # ┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──
    # INTERFACE

    async def shelf_has(self, key):
        return key in self.shelf

    async def shelf_put(self, key, value):
        self.shelf[key] = value
        self.shelf.sync()

    async def shelf_get(self, key):
        return self.shelf[key]

    async def shelf_keys(self):
        return list(self.shelf.keys())

    async def shelf_sync(self):
        """Sync'ing a shelf is similar to SQL's commit operation (assuming that writeback==False)

        **Note** ServerCommands_Shelf is not aware of whether the shelf was opened with writeback==True or ==False
        (see https://docs.python.org/3/library/shelve.html for further explanation)."""
        self.shelf.sync()

    async def shelf_del(self, key):
        """Deletes shelf item identified by key."""
        del self.shelf[key]
        self.shelf.sync()

    async def shelf_reset(self, flag_confirm=False):
        """Deletes everything stored in shelf. **Careful!!!**"""
        flag_confirm = a107.to_bool(flag_confirm)
        if flag_confirm:
            for key in self.shelf.keys():
                del self.shelf[key]
                print(f"DDDDDDDDDDDDDDDDDDDDDDDDDDDeleted {key}")
            self.shelf.sync()
