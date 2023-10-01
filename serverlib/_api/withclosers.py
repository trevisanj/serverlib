__all__ = ["WithClosers"]

import serverlib as sl, asyncio, inspect, a107


class WithClosers:
    """Ancestor for whichever class uses objects that need to be closed."""
    
    def __init__(self):
        self.__closers = []
        self.__flag_called_close = False
    
    def _append_closers(self, *args):
        """
        Appends "closeable" objects for automatic and recursive close. Returns object or list of objects passed.

        From the point of view of this class, _on_close() and _do_close() are indistinct. Both are called and in no
        paticular order.

        Examples:

        Returns object passed as argument so that it can be assigned to a variable in the same line of code:
        >>> self.seriesdbclient = self._append_closers(sacca.SeriesClient())

        In this example, a list is returned:
        >>> self.seriesdbclient, self.twitterdbclient = self._append_closers(sacca.SeriesClient(),
        >>>                                                                  sacca.TwitterDBClient())
        """
        ret = []
        for closers in args:
            if not isinstance(closers, (list, tuple)): 
                closers = [closers]
            for closer in closers:
                self.__append_closer(closer)
                ret.append(closer)
        assert len(ret) > 0, f"Nothing was passed to {self.__class__.__name__}._append_closers()"

        if len(ret) == 1: return ret[0]
        return ret

    def __append_closer(self, closer):
        assert closer not in self.__closers, (f"{closer.__class__.__name__} '{closer.name}' is already in"
            f"{self.__class__.__name__} '{self.name}'s closers")

        self.__closers.append(closer)

    _append_closer = _append_closers
    _append_closer.__name__ = "_append_closer"

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INHERITABLES

    async def _on_close(self):
        """Inherit to implement clean-up operations in subclasses outside serverlib."""

    async def _do_close(self):
        """This method is called after _on_close(). It inherited by Client. Do not inherit further outside serverlib."""

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INTERFACE

    async def close(self):
        """Calls self._on_close() and self._do_close() first; then calls closers' close()."""

        assert not self.__flag_called_close, f"{self.__class__.__name__}.close() has already been called (my name is '{self.name}')"

        self.logger.debug(f"{self.__class__.__name__} '{self.name}' is closing itself")

        await self._on_close()
        await self._do_close()

        # Separates awaitables and non-awaitables
        awaitables = []
        for closer in self.__closers:
            flag_has = True
            try:
                method = closer.close
            except AttributeError:
                try:
                    method = closer.Close
                except AttributeError:
                    flag_has = False
            if not flag_has:
                raise AttributeError(f"Class {closer.__class__.__name__} does not have close()/Close() method")

            # debug
            name = f"'{closer.name}'" if hasattr(closer, "name") else id(closer)
            self.logger.debug(f"{self.__class__.__name__} '{self.name}' is closing {closer.__class__.__name__} {name}")
            if not inspect.iscoroutinefunction(method):
                method()
            else:
                await method()

                # 20230922 using asyncio.gather() to initialize and close makes it harder to debug
                # awaitables.append(method())

        # await asyncio.gather(*awaitables)
        self.__flag_called_close = True

        self.logger.debug(f"{self.__class__.__name__} '{self.name}' finished closing itself")

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # FOR DESCENDANTS' INTERNAL USE

    async def _initialize_closers(self):
        awaitables = []
        for closer in self.__closers:

            if closer.__class__.__name__ == "ViriyaToolbox":
                print("////////////////////////////////////////////////////////////////////////////////////////")

            # debug
            name = f"'{closer.name}'" if hasattr(closer, "name") else id(closer)
            msg =f">>>>> {self.__class__.__name__} '{self.name}' WILL INITIALIZE {closer.__class__.__name__} {name}"
            self.logger.debug(msg)

            try:
                method = closer.initialize

                if not inspect.iscoroutinefunction(method):
                    method()
                else:
                    await method()
            except AttributeError:
                pass

