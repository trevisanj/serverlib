# todo 20230905 cleanup for agent client, I am inheriting from sl.Client now
# __all__ = ["AgentClient"]
#
# import serverlib as sl
#
#
# class AgentClient(sl.Client):
#     """Class for client for AgentServer
#
#     Args:
#         dbclientgetter: callable that must return a db client (this is a callable (and not a simple
#                         class name) to introduce flexibility in initializing this object)
#     """
#
#     def __init__(self, *args, dbclientgetter, **kwargs):
#         sl.Client.__init__(self, *args, **kwargs)
#         self.__dbclientgetter = dbclientgetter
#         self._attach_cmd(_ClientCommands_Agent())
#
#     # INTERFACE ZONE ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱
#
#     def get_dbclient(self):
#         return self.__dbclientgetter()
#
#
# class _ClientCommands_Agent(sl.ClientCommands):
#     """Attach this to clients to agent servers."""
#
#     async def _on_initialize(self):
#         self.dbclient = self._append_closers(self.master.get_dbclient())
#
#     async def getd_tasks(self, where=""):
#         """Runs DB server's getd_tasks()."""
#         return await self.dbclient.execute("getd_tasks", where)
