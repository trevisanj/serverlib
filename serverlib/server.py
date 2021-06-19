"""Server, ServerCommands etc."""
import pickle, os, signal, asyncio, random, a107, zmq, zmq.asyncio, serverlib as sl, traceback, random
from colored import fg, bg, attr
from .basicservercommands import *
__all__ = ["Server", "CommandError", "ST_INIT", "ST_ALIVE", "ST_LOOP", "ST_STOPPED"]


# Server states
ST_INIT = 0     # still in __init__()
ST_ALIVE = 10    # passed __init__()
ST_LOOP = 30     # in main loop
ST_STOPPED = 40  # stopped


class Server(sl.WithCommands):
    """Server class.

    Args:
        cfg: ServerConfig
        cmd: instance or list of Servercommands
        flag_basiccommands: whether to automatically attach the basic commands."""

    @property
    def logger(self):
        return self.cfg.logger

    @property
    def state(self):
        return self.__state

    @property
    def sleepers(self):
        return self.__sleepers

    @property
    def lo_ops(self):
        return self.__lo_ops

    def __init__(self, cfg, cmd=None, flag_basiccommands=True):
        super().__init__()
        self.__state = ST_INIT
        self.cfg = cfg
        cfg.master = self
        self.__sleepers = {}  # {name: _Sleeper, ...}
        self.__lo_ops = None  # {methodname:
        self._attach_cmd(_EssentialServerCommands())
        if flag_basiccommands: self._attach_cmd(BasicServerCommands())
        if cmd is not None: self._attach_cmd(cmd)
        self.__state = ST_ALIVE

    # ┌─┐┬  ┬┌─┐┬─┐┬─┐┬┌┬┐┌─┐  ┌┬┐┌─┐
    # │ │└┐┌┘├┤ ├┬┘├┬┘│ ││├┤   │││├┤
    # └─┘ └┘ └─┘┴└─┴└─┴─┴┘└─┘  ┴ ┴└─┘

    async def _on_destroy(self): pass
    async def _on_run(self): pass
    async def _after_cycle(self): pass

    # ┬ ┬┌─┐┌─┐  ┌┬┐┌─┐
    # │ │└─┐├┤   │││├┤
    # └─┘└─┘└─┘  ┴ ┴└─┘
    # http://patorjk.com/software/taag/#p=display&f=Calvin%20S&t=use%20me

    async def get_configuration(self):
        """Returns tabulatable (rows, ["key", "value"] self.cfg + additional in-server information."""
        # TODO return as dict, but create a nice visualization at the client side
        _ret = self.cfg.to_dict()
        ret = list(_ret.items()), ["key", "value"]
        return ret

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
        my_debug = lambda s: self.logger.debug(f"😴 {self.__class__.__name__}.sleep() {sleeper.name} {waittime:.3f} seconds {s}")

        async def ensure_new_name():
            i = 0
            while sleeper.name in self.__sleepers:
                if name is not None:
                    # self.stop()
                    msg = f"Called {self.__class__.__name__}.sleep({waittime}, '{name}') when '{name}' is already sleeping!"
                    raise RuntimeError(msg)
                sleeper.name += (" " if i == 0 else "")+chr(random.randint(65, 65+25))
                i += 1

        if isinstance(waittime, sl.Retry): waittime = waittime.waittime
        interval = min(waittime, 0.1)
        sleeper = _Sleeper(waittime, name)
        await ensure_new_name()
        self.__sleepers[sleeper.name] = sleeper
        slept = 0
        try:
            my_debug("💤💤💤")
            while slept < waittime and not sleeper.flag_wake_up:
                await asyncio.sleep(interval)
                slept += interval
        finally:
            my_debug("⏰WAKE⏰UP!⏰")
            try: del self.__sleepers[sleeper.name]
            except KeyError: pass

    async def run(self):
        # Automatically figures out all methods containing the word "loop" in them
        attrnames = [attrname for attrname in dir(self) if "loop" in attrname]
        self.logger.debug(f"About to await on {attrnames}")

        async def loopcoro(attrname):
            # - Waits until main loop is ready (if secondary loop)
            # - Catches cancellation: I am sort of figuring out concurrency still, and want to see exactly how each loop
            #   ends, and what are the best practices
            awaitable = getattr(self, attrname)()
            try:
                if not attrname.endswith("__serverloop"):  # secondary loop waits until primary loop is ready
                    while self.state != sl.ST_LOOP: await asyncio.sleep(0.01)
                return await awaitable
            except BaseException as e:
                self.__lo_ops[attrname].errormessage = a107.str_exc(e)
                if isinstance(e, asyncio.CancelledError): return e
                # BUGZONE BUGZONE BUGZONE BUGZONE BUGZONE BUGZONE BUGZONE BUGZONE BUGZONE BUGZONE
                # Here is the unified place to decide what to do with high-bug-probability errors
                print(f"🐛🐛🐛 {attr('bold')}Crash in {self.__class__.__name__}.{attrname}(){attr('reset')} 🐛🐛🐛")
                traceback.print_exc()
                raise

        def create_task(attrname):
            task = asyncio.create_task(loopcoro(attrname), name=attrname)
            task.errormessage = None
            task.marked = False  # marked to die, like Guts
            return task

        self.__lo_ops = {attrname: create_task(attrname) for attrname in attrnames}
        results = await asyncio.gather(*self.__lo_ops.values(), return_exceptions=True)
        self.logger.debug(f"*** Server {self.cfg.prefix} -- how the story ended: ***")
        for name, result in zip(attrnames, results):
            if isinstance(result, BaseException): result = a107.str_exc(result)
            self.logger.debug(f"{name}(): {result}")

    def stop(self):
        if self.__lo_ops is not None:
            for task in self.__lo_ops.values():
                if not task.marked:
                    task.marked = True
                    # print(f"stop() cancelling {task}")
                    task.cancel()

    # ┬  ┌─┐┌─┐┬  ┬┌─┐  ┌┬┐┌─┐  ┌─┐┬  ┌─┐┌┐┌┌─┐
    # │  ├┤ ├─┤└┐┌┘├┤   │││├┤   ├─┤│  │ ││││├┤
    # ┴─┘└─┘┴ ┴ └┘ └─┘  ┴ ┴└─┘  ┴ ┴┴─┘└─┘┘└┘└─┘

    async def __serverloop(self):
        async def execute_command(method, data):
            """(callable, list) --> (result or exception) (only raises BaseException)."""
            try: ret = await method(*data[0], **data[1])
            except Exception as e:
                if sl.flag_log_traceback:
                    a107.log_exception_as_info(self.logger, e, f"Error executing '{method.__name__}'")
                else: self.logger.info(f"Error executing '{method.__name__}': {a107.str_exc(e)}")
                ret = e
            return ret

        def parse_statement(st):
            """bytes --> (commandname, has_data, data, command, exception) (str, bool, bytes, callable, CommandError/None)."""
            bdata, data, command, exception = b"", [], None, None
            # Splits statement
            try: idx = st.index(b" ")
            except ValueError: commandname = st.decode()
            else: commandname, bdata = st[:idx].decode(), st[idx+1:]
            has_data = len(bdata) > 0
            # Figures out method
            try: command = self.commands_by_name[commandname]
            except KeyError:
                message = f"Command is non-existing: '{commandname}'"
                self.logger.info(message)
                exception = CommandError(message)
            else: self.cfg.logger.info(f"$ {commandname}{' ...' if has_data else ''}")
            # Processes data
            if command:
                data = [[], {}] if len(bdata) == 0 else [[bdata], {}] if command.flag_bargs else pickle.loads(bdata)
                if not isinstance(data, list):
                    exception = CommandError(f"Data must unpickle to a list, not a {data.__class__.__name__}")
                elif len(data) != 2 or type(data[0]) not in (list, tuple) or type(data[1]) != dict:
                    exception = CommandError("Data must unpickle to a structure like this: [[...], {...}]")
            return commandname, has_data, data, command, exception

        async def recv_send():
            try:
                st = await sck_rep.recv()
                commandname, has_data, data, command, exception = parse_statement(st)
                if exception: result = exception
                else: result = await execute_command(command.method, data)
                msg = pickle.dumps(result)
                await sck_rep.send(msg)
            except zmq.Again: return False
            return True

        # INITIALIZATION
        def _ctrl_z_handler(signum, frame):
            print("Don't press Ctrl+Z 😠, or clean-up code won't be executed 😱; Ctl+C should do thou 😜")
            flag_leave[0] = True
        signal.signal(signal.SIGTSTP, _ctrl_z_handler)
        signal.signal(signal.SIGTERM, _ctrl_z_handler)
        flag_leave = [False]

        self.cfg.read_configfile()
        a107.ensure_path(self.cfg.datadir)
        ctx = zmq.asyncio.Context()
        sck_rep = ctx.socket(zmq.REP)
        logmsg = f"Binding ``{self.cfg.prefix}'' (REP) to {self.cfg.url} ..."
        self.cfg.logger.info(logmsg)
        if not self.cfg.flag_log_console: print(logmsg) # If not logging to console, prints sth anyway (helps a lot)
        sck_rep.bind(self.cfg.url)
        await self._on_run()
        await self._initialize_cmd()
        # MAIN LOOP ...
        self.__state = ST_LOOP
        try:
            while True:
                did_sth = await recv_send()
                await self._after_cycle()
                if not did_sth:
                    # Sleeps because tired of doing nothing
                    if self.cfg.sleepinterval > 0: await asyncio.sleep(self.cfg.sleepinterval)
        except asyncio.CancelledError: raise
        except KeyboardInterrupt: return "⌨ K ⌨ E ⌨ Y ⌨ B ⌨ O ⌨ A ⌨ R ⌨ D ⌨"
        except:
            self.cfg.logger.exception(f"Server '{self.cfg.prefix}' ☠C☠R☠A☠S☠H☠E☠D☠")
            raise
        finally:
            self.__state = ST_STOPPED
            self.cfg.logger.debug(f"😀 DON'T WORRY 😀 {self.__class__.__name__}.__serverloop() 'finally:'")
            self.wake_up()
            await asyncio.sleep(0.1); self.stop()  # Thought I might wait a bit before cancelling all loops
            sck_rep.close()
            ctx.destroy()
            await self._on_destroy()


class CommandError(Exception):
    pass


class _Sleeper:
    def __init__(self, seconds, name=None):
        self.seconds = seconds
        self.name = a107.random_name() if name is None else name
        self.task = None
        self.flag_wake_up = False


class _EssentialServerCommands(sl.ServerCommands):
    async def _get_welcome(self):
        return "\n".join(a107.format_slug(f"Welcome to the '{self.master.cfg.prefix}' server", random.randint(0, 2)))

    async def _get_name(self):
        """Returns the server application name."""
        return self.cfg.applicationname

    async def _get_prefix(self):
        """Returns the server prefix."""
        return self.cfg.prefix

    async def _poke(self):
        """Prints and returns the server prefix (useful to identify what is running in a terminal)."""
        # print(f"👉 {self.cfg.prefix}")  # 👈")
        print(f"{fg('white')}{attr('bold')}{self.cfg.prefix}{attr('reset')} 👈")
        return self.cfg.prefix
