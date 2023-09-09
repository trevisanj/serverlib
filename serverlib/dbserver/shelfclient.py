"""Parts for multiple inheritance (God protect me)."""
import serverlib as sl

__all__ = ["ShelfClient"]

class ShelfClient:
    """Accesses shelf throught self.dbclient."""

    dbclient: sl.Client

    async def shelf_get(self, key, default=None):
        # try:
        #     return await self.dbclient.execute_server("shelf_get", key)
        # except KeyError: return default

        # Avoids causing exceptions in server because exceptions are scary
        if await self.dbclient.execute("shelf_has", key):
            return await self.dbclient.execute_server("shelf_get", key)
        return default

    async def shelf_put(self, key, value):
        return await self.dbclient.execute_server("shelf_put", key, value)

    async def shelf_has(self, key):
        return await self.dbclient.execute_server("shelf_has", key)

    async def shelf_sync(self):
        return await self.dbclient.execute_server("shelf_sync")

    async def shelf_keys(self):
        return await self.dbclient.execute_server("shelf_keys")

    async def shelf_del(self, key):
        return await self.dbclient.execute_server("shelf_del", key)