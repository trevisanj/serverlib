__all__ = ["WithClosers"]

import serverlib as sl, asyncio, inspect, a107


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
        >>> self.seriesdbclient = self._append_closers(sacca.SeriesClient())

        In this example, a list is returned:
        >>> self.seriesdbclient, self.twitterdbclient = self._append_closers(sacca.SeriesClient(),
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
        """Inherit to implement clean-up operations in subclasses outside serverlib."""

    async def _do_close(self):
        """This method is called after _on_close(). It inherited by Client. Do not inherit further outside serverlib."""

    # INTERFACE

    async def close(self):
        """Calls self._on_close() and self._do_close() first; then calls closers' close()."""

        assert not self.__flag_called_close, f"{self.__class__.__name__}.close() has already been called"

        self.logger.debug(f"Closing {self.__class__.__name__}")

        await self._on_close()
        await self._do_close()

        # Separates awaitables and non-awaitables
        awaitables = []
        for closer in self.__closers:
            flag_has = True
            try: method = closer.close
            except AttributeError:
                try:
                    method = closer.Close
                except AttributeError:
                    flag_has = False
            if not flag_has:
                raise AttributeError(f"Class {closer.__class__.__name__} does not have close()/Close() method")

            if not inspect.iscoroutinefunction(method):
                method()
            else:
                awaitables.append(method())

        await asyncio.gather(*awaitables)
        self.__flag_called_close = True

