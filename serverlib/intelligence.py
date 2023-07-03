__all__ = ["Intelligence",]

import a107, serverlib as sl, asyncio, inspect


class Intelligence(sl.WithClosers):
    """
    Intelligence base class: master, server, logger, cfg, initialize(), close(), get_meta() etc.

    It does not necessarily require a server nor initialization.
    """

    # Custom title for this class, e.g. appearing as the title of a group of commands in help text
    _title = None
    # Methods that shouldn't be exposed as commands
    _excluded = []

    @property
    def title(self):
        if self._title: return self._title
        return self.__class__.__name__

    @property
    def logger(self):
        if self.__logger is None:
            if self.master and hasattr(self.master, "logger"):
                self.__logger = self.master.logger
            elif self.master and hasattr(self.master, "cfg") and hasattr(self.master.cfg, "logger"):
                self.__logger = self.master.cfg.logger
            else:
                self.__logger = a107.get_python_logger()
        return self.__logger

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

        self.name = a107.random_name()
        # print(f"AND A NEW INTELLIGENCE IS BORN: {self.name} ({self.__class__.__name__})--------------------------------------")

    # INHERITABLES

    async def _on_initialize(self):
        pass

    # INTERFACE

    def get_meta(self, flag_protected=True):
        """Creates list of MetaCommand's based on own methods, which are filtered according to get_methods() rules."""
        return [sl.MetaCommand(method) for method in self.get_methods(flag_protected)]

    def get_methods(self, flag_protected=False):
        """Return list of methods according to filter rules."""

        _SUPEREXCLUDED = ("initialize", "close", "get_methods", "get_meta")
        return [x[1] for x in inspect.getmembers(self, predicate=inspect.ismethod)
                if "__" not in x[0]
                and not x[0].startswith(("_on_", "_do_", "_append_closer", "_aappend_closer",
                                         "_i_",  # #convention for internal commands not to be picked up by get_methods()
                                         ))
                and (flag_protected or not x[0].startswith("_"))
                and x[0] not in _SUPEREXCLUDED and x[0] not in self._excluded]

    async def initialize(self):
        """Initializes. May be called only once."""
        assert not self.__flag_initialized
        await self._on_initialize()

    async def ensure_initialized(self):
        """Initializes if not so yet."""
        if not self.__flag_initialized:
            await self.initialize()
