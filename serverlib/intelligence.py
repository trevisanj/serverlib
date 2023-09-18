__all__ = ["Intelligence"]

import a107, serverlib as sl, inspect
from . import _api


class Intelligence(_api.WithClosers):
    """
    Intelligence base class: master, server, logger, cfg, initialize(), close(), get_meta() etc.

    It does not necessarily require a server nor initialization.
    """

    # Custom title for this class, e.g. appearing as the title of a group of commands in help text
    _title = None

    @property
    def title(self):
        if self._title: return self._title
        return self.__class__.__name__

    @property
    def logger(self):
        return self.master.logger

    @property
    def cfg(self):
        if self.__cfg is None:
            if self.master and hasattr(self.master, "cfg"):
                self.__cfg = self.master.cfg
        return self.__cfg

    @property
    def server(self):
        if isinstance(self.master, sl.Server): return self.master
        if hasattr(self.master, "server"): return self.master.server
        return None

    @property
    def client(self):
        if isinstance(self.master, sl.Client): return self.master
        return None

    def __init__(self, master=None, cfg=None):
        super().__init__()
        self.master = master
        self.__logger = None
        self.__cfg = cfg
        self.__flag_initialized = False

        # TODO this is stupid but I should fix this only when I do need name for intelligence
        self.name = a107.random_name()
        # print(f"AND A NEW INTELLIGENCE IS BORN: {self.name} ({self.__class__.__name__})--------------------------------------")

    # INHERITABLES

    async def _on_initialize(self):
        pass

    # INTERFACE

    async def initialize(self):
        """Initializes. May be called only once."""
        assert not self.__flag_initialized
        await self._on_initialize()

    async def ensure_initialized(self):
        """Initializes if not so yet."""
        if not self.__flag_initialized:
            await self.initialize()
