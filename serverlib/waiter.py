__all__ = ["Waiter"]


import serverlib as sl


class Waiter(sl.Intelligence):
    """Little useful server-side feature to help with progressive delaying (when an operation fails repeatedly).

    Requires a server, hence sl.Intelligence.
    """

    def __init__(self, *args, waittime=None, maxtries=None, maxwaittime=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.waittime = sl.waiter_waittime if waittime is None else waittime
        self.maxtries = sl.waiter_maxtries if maxtries is None else maxtries
        self.maxwaittime = sl.waiter_waittime if maxwaittime is None else maxwaittime
        self.numtries = 0

    async def wait_or_raise(self, msg):
        msg_ = f"{msg}  (attempt {self.attemptstr()})"
        if self.flag_persevere():
            self.logger.info(f"{msg_} (retrying after {self.waittime:.2f} seconds)")
            await self.wait()
        else:
            raise sl.Retry(f"{msg_} (gave up)")

    def attemptstr(self):
        return f"{self.numtries+1}/{self.maxtries}"

    def flag_persevere(self):
        return self.numtries < self.maxtries

    def flag_give_up(self):
        return self.numtries >= self.maxtries

    async def wait(self):
        await self.server.sleep(self.waittime)
        self.waittime = min(self.waittime*1.618, self.maxwaittime)
        self.numtries += 1
