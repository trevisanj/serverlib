import a107, serverlib as sl
__all__ = ["Intelligence"]


class Intelligence:
    """Intelligence base class: master, server, logger, cfg, initialize() and close()."""
    _name = None

    @property
    def name(self):
        if self._name: return self._name
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
        elif isinstance(self.master, sl.Client): return None
        if not hasattr(self.master, "server"):
            raise TypeError("self.master must either be a serverlib.Server or have a 'server' attribute")
        return self.master.server

    def __init__(self, master):
        self.master = master
        self.__logger = None
        self.__cfg = None

    # INHERITABLES

    async def close(self):
        pass

    async def initialize(self):
        pass
