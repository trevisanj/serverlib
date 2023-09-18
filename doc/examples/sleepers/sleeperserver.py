#!/usr/bin/env python
import serverlib as sl, a107, argparse, random as ra, textwrap, asyncio, traceback, time
__doc__ = """Creates "sleepers" on the server -- an idea to test and illustrate the thing with throwing CancelledError."""


class Sleeper:
    def __init__(self, seconds):
        sl.lowstate.sleeperid += 1
        self.id_ = sl.lowstate.sleeperid
        self.seconds = seconds
        self.name = a107.random_name()
        self.created_at = time.time()
        self.task = None

class SleeperCommands(sl.ServerCommands):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__sleepers = []

    @sl.is_command
    async def create(self, seconds):
        """Creates sleeper that sleeps seconds."""
        seconds = float(seconds)
        async def sleeperlife(sleeper):
            self.__sleepers.append(sleeper)
            try:
                print(f"ZZZ {sleeper.name} -- {sleeper.seconds} second(s)")
                await self.master.sleep(sleeper.seconds)
                print(f"ZZZ {sleeper.name} -- {sleeper.seconds} .... ooooo OOOOOO YAAAAAWWWNNN (woke up)")
            except BaseException as e:
                print(f"ZZZ {sleeper.name} caught sth ({a107.str_exc(e)}) ... gonna die anyway")
            finally:
                print(f"ZZZ {sleeper.name} -- goodbye world!")
                self.__sleepers.remove(sleeper)

        sleeper = Sleeper(seconds)
        sleeper.task = asyncio.create_task(sleeperlife(sleeper))
        return sleeper.name

    @sl.is_command
    async def list(self):
        """List all sleepers"""
        ret = [{"id": sleeper.id_,
                "name": sleeper.name,
                "seconds": sleeper.seconds,
                "created_at": a107.ts2str(sleeper.created_at),
                "seconds_left": sleeper.seconds-(time.time()-sleeper.created_at)} for sleeper in self.__sleepers]
        return ret

    @sl.is_command
    async def killall(self):
        """Kills all sleepers"""
        for sleeper in self.__sleepers:
            sleeper.task.cancel()

    @sl.is_command
    async def kill(self, id_):
        """Kills sleeper identified by id_ (use "list" to find out ids)"""
        id_ = int(id_)
        found = False
        for sleeper in self.__sleepers:
            if sleeper.id_ == id_:
                sleeper.task.cancel()
                found = True
        if not found:
            raise ValueError(f"Sleeper id not found: {id_}")



if __name__ == "__main__":
    sl.lowstate.sleeperid = 0

    cfg = sl.ServerCfg(port=6667,
                          flag_log_console=True,
                          appname="sleeper",
                          description=__doc__)
    server = sl.Server(cfg, cmd=SleeperCommands())
    sl.cli_server(server)
