__all__ = ["WithCommands", "WithClosers", "WithSleepers"]

import serverlib as sl, asyncio, inspect, a107, random

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
            cmds: each element may be a Commands or [Commands0, Commands1, ..]

        **Note** This method may be called from __init__().
        """
        for cmd in cmds:
            if not isinstance(cmd, (list, tuple)): cmd = [cmd]
            for _ in cmd:
                if not isinstance(_, sl.Intelligence):
                    raise TypeError(f"Invalid commands type: {_.__class__.__name__} (must be an Intelligence)")
            for _ in cmd:
                _.master = self
                self.cmd[_.title] = _
                for metacommand in _.get_meta(flag_protected=True):
                    name = metacommand.name
                    # WARNING: #gambiarra ahead
                    if name in self.metacommands and name not in ["getd_cfg"]:
                        print(a107.format_warning(f"Repeated command: '{name}'"))  # TODO let's see, maybe we let commands override each other
                    self.metacommands[name] = metacommand


class WithClosers:
    """Ancestor for whichever class uses objects that need to be closed."""
    
    def __init__(self):
        self.__closers = []
        self.__flag_called_close = False
    
    def _append_closers(self, *args):
        """Appends "closeable" objects for automatic and recursive close. Returns object or list of objects passed.

        From the point of view of this class, _on_close() and _do_close() are indistinct. Both are called and in no
        paticular order.

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

    async def _aappend_closers(self, *args, flag_initialize=True):
        """Async version of _append_closers() with automatic initialization option."""
        ret = []
        for closers in args:
            if not isinstance(closers, (list, tuple)): closers = [closers]
            for closer in closers:
                self.__closers.append(closer)
                ret.append(closer)
        assert len(ret) > 0, f"Nothing was passed to {self.__class__.__name__}._append_closers()"

        if flag_initialize:
            await asyncio.gather(*[closer.initialize() for closer in ret if hasattr(closer, "initialize")])

        if len(ret) == 1: return ret[0]
        return ret

    _append_closer = _append_closers
    _append_closer.__name__ = "_append_closer"
    _aappend_closer = _aappend_closers
    _append_closers.__name__ = "_append_closers"

    # INHERITABLES

    async def _on_close(self):
        pass

    async def _do_close(self):
        pass

    # INTERFACE

    async def close(self):
        """Calls self._on_close() and self._do_close() first; then calls closers' close()."""
        assert not self.__flag_called_close, f"{self.__class__.__name__}.close() has already been called"
        self.logger.debug(f"Clooooooooooooooooooooooooooooooooooosando {self.__class__.__name__}")

        await asyncio.gather(self._on_close(), self._do_close())

        # Separates awaitables and non-awaitables
        awaitables = []
        for closer in self.__closers:
            flag_has = True
            try: method = closer.close
            except AttributeError:
                try: method = closer.Close
                except AttributeError: flag_has = False
            if not flag_has:
                raise AttributeError(f"Class {closer.__class__.__name__} does not have close()/Close() method")

            if not inspect.iscoroutinefunction(method):
                method()
            else:
                awaitables.append(method())
        await asyncio.gather(*awaitables)
        self.__flag_called_close = True


class WithSleepers:
    @property
    def sleepers(self):
        return self.__sleepers

    def __init__(self):
        self.__sleepers = {}  # {name: _Sleeper, ...}

    def wake_up(self, sleepername=None):
        """Cancel all "naps" created with self.sleep(), or specific one specified by sleepername."""
        if sleepername is not None:
            self.__sleepers[sleepername].flag_wake_up = True
        else:
            for sleeper in self.__sleepers.values(): sleeper.flag_wake_up = True

    async def wait_a_bit(self):
        """Unified way to wait for a bit, usually before retrying something that goes wront."""
        await self.sleep(0.1)

    async def sleep(self, waittime, name=None):
        """Takes a nap that can be prematurely terminated with self.wake_up()."""
        try: logger = self.logger
        except AttributeError: logger = a107.get_python_logger()
        my_debug = lambda s: logger.debug(
            f"😴 {self.__class__.__name__}.sleep() {sleeper.name} {waittime:.3f} seconds {s}")

        async def ensure_new_name(name):
            i = 0
            while sleeper.name in self.__sleepers:
                if name is not None:
                    msg = f"Called {self.__class__.__name__}.sleep({waittime}, '{name}') when '{name}' is already sleeping!"
                    raise RuntimeError(msg)
                sleeper.name += (" " if i == 0 else "")+chr(random.randint(65, 65+25))
                i += 1

        if isinstance(waittime, sl.Retry): waittime = waittime.waittime
        interval = min(waittime, 0.1)
        sleeper = _Sleeper(waittime, name)
        await ensure_new_name(name)
        self.__sleepers[sleeper.name] = sleeper
        slept = 0
        try:
            my_debug("💤💤💤")
            while slept < waittime and not sleeper.flag_wake_up:
                await asyncio.sleep(interval)
                slept += interval
        finally:
            my_debug("⏰WAKE⏰UP!⏰")
            try:
                del self.__sleepers[sleeper.name]
            except KeyError:
                pass


class _Sleeper:
    def __init__(self, seconds, name=None):
        self.seconds = seconds
        self.name = a107.random_name() if name is None else name
        self.task = None
        self.flag_wake_up = False
