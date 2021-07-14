#!/usr/bin/env python
import serverlib, a107, argparse, random as ra, textwrap, asyncio, traceback
__doc__ = """Creates "sleepers" on the server -- an idea to test and illustrate the thing with throwing CancelledError."""


class Sleeper:
    def __init__(self, seconds):
        self.seconds = seconds
        self.name = a107.random_name()
        self.task = None

class SleeperCommands(serverlib.ServerCommands):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__sleepers = []

    async def random_name(self):
        """Generates a random human name."""
        return a107.random_name()

    async def create(self, seconds):
        """Creates sleeper that sleepes seconds."""
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

    async def sleepers(self):
        ret = [(sleeper.name, sleeper.seconds) for sleeper in self.__sleepers]
        return ret

    async def killall(self):
        for sleeper in self.__sleepers:
            sleeper.task.cancel()


def main(args):
    cfg = serverlib.ServerConfig()
    cfg.host = args.host
    cfg.port = args.port
    cfg.flag_log_console = True
    cfg.appname = "sleeper"
    cfg.description = __doc__
    server = serverlib.Server(cfg, cmd=SleeperCommands())
    asyncio.run(server.run())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("--host", type=str, help="host", default=None)
    parser.add_argument('port', type=int, help='port', nargs="?", default=6667)

    args = parser.parse_args()
    main(args)
