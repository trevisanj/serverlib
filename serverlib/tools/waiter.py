__all__ = ["Waiter"]


import serverlib as sl


class Waiter(sl.Intelligence):
    """Little useful server-side feature to help with progressive delaying (when an operation fails repeatedly).

    Args:
        description: string to show at the beginning of logging messages
        time_start: start waiting time
        time_max: maximum waiting time
        maxtries: maximum number of tries for wait_or_raise()

    In order to wait, uses server's "sleeper" feature, hence sl.Intelligence.
    """

    # @property
    # def nextwaittime(self):
    #     return self.__nextwaittime

    @property
    def nexttime(self):
        return self.__nexttime
    #
    # @property
    # def numtries(self):
    #     return self.__numtries

    @property
    def flag_give_up(self):
        return self.__numtries >= self.__maxtries

    @property
    def flag_persevere(self):
        return not self.flag_give_up

    def __init__(self, *args, description=None, time_start=None, maxtries=None, time_max=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Default message if none is specified at wait() or wait_or_raise()
        self.description = description
        self.__nexttime = self.__starttime = sl.config.waiter_time_start if time_start is None else time_start
        self.__maxtries = sl.config.waiter_maxtries if maxtries is None else maxtries
        self.__maxtime = sl.config.waiter_time_max if time_max is None else time_max
        self.__numtries = 0

    def reset(self):
        """Restarts counter and progression of time."""
        self.__numtries = 0
        self.__nexttime = self.__starttime

    async def wait(self):
        self.logger.info(self.__msgstr(float("inf")))
        await self._quietwait()

    async def wait_or_raise(self):
        """Waits or raises serverlib.Retry if reached maxtries."""
        if self.__numtries < self.__maxtries:
            self.logger.info(self.__msgstr())
            await self._quietwait()
        else:
            raise sl.Retry(self.__msgstr())

    async def _quietwait(self):
        """Waits as is maxtries were infinite"""
        await self.server.sleep(self.__nexttime)
        self.__nexttime = min(self.__nexttime * 1.618, self.__maxtime)
        self.__numtries += 1

    def __msgstr(self, maxtries=None):
        if maxtries is None: maxtries = self.__maxtries
        if self.__numtries < maxtries:
            what = f"waiting {self.__nexttime:.2f} seconds"
        else:
            what = "gave up!"
        return f"{self.__description}: attempt {self.__numtries + 1}/{maxtries}; {what}"
