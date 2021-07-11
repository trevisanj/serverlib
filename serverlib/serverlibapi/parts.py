__all__ = ["WithCommands", "WithClosers"]

import serverlib as sl, asyncio

class WithCommands:
    """This class enters as an ancestor for the Client and Server class in a multiple-inheritance composition."""

    def __init__(self):
        # {name: Command, ...}
        self.cmd = {}
        # {commandname: Command, ...}, synthesized from all self.cmd
        self.metacommands = {}

    async def _initialize_cmd(self):
        await asyncio.gather(*[cmd.initialize() for cmd in self.cmd.values()])

    def _attach_cmd(self, *cmds):
        """Attaches one or more Commands instances.

        Args:
            cmds: each element may be a Command or [Command0, Command1, ..]

        **Note** This method may be called from __init__().
        """
        for cmd in cmds:
            if not isinstance(cmd, (list, tuple)): cmd = [cmd]
            for _ in cmd:
                if not isinstance(_, sl.Intelligence):
                    raise TypeError(f"Invalid commands type: {_.__class__.__name__}")
            for _ in cmd:
                _.master = self
                self.cmd[_.title] = _
                for metacommand in _.get_meta(flag_protected=True):
                    self.metacommands[metacommand.name] = metacommand


class WithClosers:
    """Ancestor for whichever class uses objects that need to be closed."""
    
    def __init__(self):
        self.__closers = []
        self.__flag_called_close = False
    
    def _append_closers(self, *args):
        """Appends "closeable" objects for automatic and recursive close. Returns object or list of objects passed.

        Examples:

        Returns object passed as argument so that it can be assigned to a variable in the same line of code:
        >>> self.seriesdbclient = self._append_closers(sacca.SeriesDBClient())

        In this example, a list is returned:
        >>> self.seriesdbclient, self.twitterdbclient = self._append_closers(sacca.SeriesDBClient(),
        >>>                                                                 sacca.TwitterDBClient())
        """
        ret = []
        for closers in args:
            if not isinstance(closers, (list, tuple)): closers = [closers]
            for closer in closers:
                self.__closers.append(closer)
                ret.append(closer)
        assert len(ret) > 0, f"Nothing was passed to {self.__class__.__name__}._append_closers()"
        if len(ret) == 1: return ret[0]
        return ret

    _append_closer = _append_closers

    # INHERITABLES

    async def _on_close(self):
        pass

    # INTERFACE

    async def close(self):
        assert not self.__flag_called_close, f"{self.__class__.__name__}.close() has already been called"
        self.logger.debug(f"Clooooooooooooooooooooooooooooooooooosando {self.__class__.__name__}")
        await asyncio.gather(*[closer.close() for closer in self.__closers], self._on_close())
        self.__flag_called_close = True
