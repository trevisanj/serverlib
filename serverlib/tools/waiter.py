__all__ = ["Waiter"]


import serverlib as sl


class Waiter(sl.Intelligence):
    """Little useful server-side feature to help with progressive delaying (when an operation fails repeatedly).

    Args:
        description: string to show at the beginning of logging messages
        starttime: start waiting time
        time_max: maximum waiting time
        maxtries: maximum number of tries for wait_or_raise()

    In order to wait, uses server's "sleeper" feature, hence sl.Intelligence.
    """

    @property
    def flag_give_up(self):
        return self.numtries >= self.maxtries

    @property
    def flag_persevere(self):
        return not self.flag_give_up

    def __init__(self, *args, description=None, sleepername=None, starttime=None, maxtries=None, time_max=None,
                 flag_quiet=False, logger=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Default message if none is specified at wait() or wait_or_raise()
        self.description = description
        self.sleepername = sleepername
        self.nexttime = self.starttime = sl.config.waiter_starttime if starttime is None else starttime
        self.maxtries = sl.config.waiter_maxtries if maxtries is None else maxtries
        self.maxtime = sl.config.waiter_maxtime if time_max is None else time_max
        self.flag_quiet = flag_quiet
        self.__actuallogger = logger if logger is not None else self.logger

        self.numtries = 0

    def reset(self):
        """Restarts counter and progression of time."""
        self.numtries = 0
        self.nexttime = self.starttime

    async def wait(self):
        """Waits as is maxtries were infinite"""
        if not self.flag_quiet:
            self.__actuallogger.info(self.msgstr(float("inf")))
        await self.quietwait()

    async def wait_or_raise(self):
        """Waits or raises serverlib.Retry if reached maxtries."""
        if self.numtries < self.maxtries:
            if not self.flag_quiet:
                self.__actuallogger.info(self.msgstr())
            await self.quietwait()
        else:
            raise sl.Retry(self.msgstr())

    async def quietwait(self):
        await self.server.sleep(self.nexttime, self.sleepername)
        self.nexttime = min(self.nexttime * 1.618, self.maxtime)
        self.numtries += 1

    def msgstr(self, maxtries=None):
        if maxtries is None:
            maxtries = self.maxtries
        if self.numtries < maxtries:
            what = f"waiting {self.nexttime:.2f} seconds"
        else:
            what = "gave up!"
        return f"{self.description}: attempt {self.numtries + 1}/{maxtries}; {what}"
