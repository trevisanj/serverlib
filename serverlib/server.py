"""Server, ServerCommands etc."""
import pickle, os, signal, asyncio, random, a107, zmq, zmq.asyncio, copy, serverlib as sl, traceback
from dataclasses import dataclass
from colored import fg, bg, attr
__all__ = ["Server", "CommandError", "BasicServerCommands", "ST_INIT", "ST_ALIVE", "ST_LOOP", "ST_STOPPED"]


class _EssentialServerCommands(sl.ServerCommands):
    async def _get_welcome(self):
        return "\n".join(a107.format_slug(f"Welcome to the '{self.master.cfg.prefix}' server", random.randint(0, 2)))

    async def _get_name(self):
        """Returns the server application name."""
        return self.cfg.applicationname

    async def _get_prefix(self):
        """Returns the server prefix."""
        return self.cfg.prefix


class BasicServerCommands(sl.ServerCommands):
    async def help(self, what=None):
        """Gets summary of available server commands or help on specific command."""
        if what is None:
            name_method = [(k, v.method) for k, v in self.master.commands_by_name.items()]
            aname = self.master.cfg.prefix
            lines = [aname, "="*len(aname)]
            if self.master.cfg.description: lines.extend(sl.format_description(self.master.cfg.description))
            lines.append("")
            lines.extend(sl.format_name_method(name_method))
            return "\n".join(lines)
        else:
            if what not in self.master.commands_by_name:
                raise ValueError("Invalid method: '{}'. Use 'help()' to list methods.".format(what))
            return sl.format_method(self.master.commands_by_name[what].method)

    async def stop(self):
        """Stops server. """
        await self.master.stop()
        return "As you wish."

    async def get_configuration(self):
        """Returns dict containing configuration information.

        Returns:
            {script_name0: filepath0, ...}
        """
        return await self.master.get_configuration()

    async def ping(self):
        """Returns "pong"."""
        return "pong"

    async def wake_up(self):
        """Gently wakes up all sleepers."""
        await self.master.wake_up()

    async def sleepers(self):
        ret = [{"name": sleeper.name, "seconds": sleeper.seconds} for sleeper in self.master.sleepers.values()]
        return ret

    # This sleepers thing started as a humorous exercise to understand task cancellation and ended up somewhat serious
    async def create_sleeper(self, seconds, name=None):
        """Creates sleeper that sleepes seconds."""
        seconds = float(seconds)
        asyncio.create_task(self.master.sleep(float(seconds), name))

    async def loops(self):
        ret = []
        for name, loopinfo in self.master.lo_ops.items():
            t = loopinfo.task
            ret.append({"name": name,
                        "status": "pending" if not t.done() else "cancelled" if t.cancelled() else "finished",
                        "errormessage": loopinfo.errormessage,
                        })
        return ret


# Server states
ST_INIT = 0     # still in __init__()
ST_ALIVE = 1    # passed __init__()
ST_LOOP = 2     # in main loop
ST_STOPPED = 3  # stopped


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

        # More init
        self.__logger = None
        self.__flag_to_stop = False # stop at next chance
        self.__recttask = None
        self.__sleepers = {}  # {name: _Sleeper, ...}
        self.__lo_ops = None
        self.ctx = None  # zmq context
        self.sck_rep = None  # ZMQ_REP socket

        self.attach_cmd(_EssentialServerCommands())
        if flag_basiccommands:
            self.attach_cmd(BasicServerCommands())
        if cmd is not None:
            self.attach_cmd(cmd)

        self.__state = ST_ALIVE

    # ┌─┐┬  ┬┌─┐┬─┐┬─┐┬┌┬┐┌─┐  ┌┬┐┌─┐
    # │ │└┐┌┘├┤ ├┬┘├┬┘│ ││├┤   │││├┤
    # └─┘ └┘ └─┘┴└─┴└─┴─┴┘└─┘  ┴ ┴└─┘

    async def _on_destroy(self):
        pass

    async def _on_run(self):
        pass

    # #generic
    async def _after_cycle(self):
        pass

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

    async def wake_up(self):
        """Cancel all "naps" created with self.sleep()."""
        for sleeper in self.__sleepers.values(): sleeper.wake_up = True

    async def wait_a_bit(self):
        """Unified way to wait for a bit, usually before retrying something that goes wront."""
        await self.sleep(0.1)

    async def sleep(self, to_wait, name=None):
        """Takes a nap that can be prematurely terminated with self.wake_up()."""
        interval = min(to_wait, 0.1)
        sleeper = _Sleeper(to_wait, name)
        self.__sleepers[sleeper.name] = sleeper
        slept = 0
        try:
            while slept < to_wait and not sleeper.wake_up:
                await asyncio.sleep(interval)
                slept += interval
        finally:
            try: del self.__sleepers[sleeper.name]
            except KeyError: pass

    async def run(self):
        def _ctrl_z_handler(signum, frame):
            """... we need this to handle the Ctrl+Z."""
            self.__stop()
        signal.signal(signal.SIGTSTP, _ctrl_z_handler)
        signal.signal(signal.SIGTERM, _ctrl_z_handler)
        self.cfg.read_configfile()
        self.ctx = zmq.asyncio.Context()
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

        self.__lo_ops = {attrname: _LoopInfo(asyncio.create_task(loopcoro(attrname), name=attrname)) for attrname in attrnames}
        results = await asyncio.gather(*[x.task for x in self.__lo_ops.values()], return_exceptions=True)
        self.logger.info(f"*** Server {self.cfg.prefix} -- how the story ended: ***")
        for name, result in zip(attrnames, results):
            if isinstance(result, BaseException): result = a107.str_exc(result)
            self.logger.info(f"{name}(): {result}")

    async def stop(self):
        if self.__lo_ops is not None:
            for x in self.__lo_ops.values(): x.task.cancel()

    # ┬  ┌─┐┌─┐┬  ┬┌─┐  ┌┬┐┌─┐  ┌─┐┬  ┌─┐┌┐┌┌─┐
    # │  ├┤ ├─┤└┐┌┘├┤   │││├┤   ├─┤│  │ ││││├┤
    # ┴─┘└─┘┴ ┴ └┘ └─┘  ┴ ┴└─┘  ┴ ┴┴─┘└─┘┘└┘└─┘

    async def __serverloop(self):
        a107.ensure_path(self.cfg.datadir)
        self.__bind_rep()
        await self._on_run()
        self.__state = ST_LOOP
        try:
            while True:
                try:
                    did_sth = await self.__recv_send()
                    if self.__check_stop(): break
                    await self._after_cycle()
                    if not did_sth:
                        # print(f"SLEEPING {self.cfg.sleepinterval} seconds because didn't do shit")
                        if self.cfg.sleepinterval > 0:
                            await asyncio.sleep(self.cfg.sleepinterval)
                    else:
                        pass
                except KeyboardInterrupt: self.__stop()
        except asyncio.CancelledError: raise
        except:
            self.cfg.logger.exception(f"Server '{self.cfg.prefix}' crashed!")
            raise
        finally:
            self.__state = ST_STOPPED
            self.cfg.logger.debug(f"{self.__class__.__name__}.__serverloop() finalliessssssssssssssssssssssssss")
            await self.wake_up()
            self.sck_rep.close()
            self.ctx.destroy()
            await self._on_destroy()

    def __bind_rep(self):
        sck_rep = self.sck_rep = self.ctx.socket(zmq.REP)
        logmsg = f"Binding ``{self.cfg.prefix}'' (REP) to {self.cfg.url    } ..."
        self.cfg.logger.info(logmsg)
        if not self.cfg.flag_log_console:
            print(logmsg) # Prints it if not logging to console, so I know it is not just a frozen program
        sck_rep.bind(self.cfg.url)

    async def __recv_send(self):
        """Returns whether did sth."""
        try:
            st = await self.sck_rep.recv()
            commandname, has_data, data, command, exception = self.__parse_statement(st)
            if exception: ret = exception
            else: ret = await self.__execute_command(command.method, data)
            msg = pickle.dumps(ret)
            await self.sck_rep.send(msg)
        except zmq.Again:
            ret = False  # time.sleep(self.cfg.sleepinterval)
        return ret

    def __check_stop(self):
        ret = False
        if os.path.exists(self.cfg.stoppath):
            self.cfg.logger.debug("Stopping because file '{}' exists".format(self.cfg.stoppath))
            try:
                os.unlink(self.cfg.stoppath)
            except (PermissionError, FileNotFoundError):
                pass

            self.__stop()
        if self.__flag_to_stop:
            self.cfg.logger.info("Somebody told me to stop.")
            ret = True
        return ret

    def __stop(self):
        self.__flag_to_stop = True

    def __parse_statement(self, st):
        """Parses statement into usable information

        Args:
            st: (bytes) statement

        Returns:
            (commandname, has_data, data, command, exception), respectively (str, bool, bytes, callable, CommandError)
        """
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

    async def __execute_command(self, method, data):
        """Processes the statement received from client.

        Args:
            method: a (callable) method from some ServerCommands class
            data: list

        Returns:
            result returned by method, or the raised exception (does not raise, returns the exception instead)
        """
        try:
            ret = await method(*data[0], **data[1])
        except Exception as e:
            a107.log_exception_as_info(self.logger, e, f"Error executing '{method.__name__}'")
            ret = e
        return ret


class CommandError(Exception):
    pass


class _Sleeper:
    def __init__(self, seconds, name=None):
        self.seconds = seconds
        self.name = a107.random_name() if name is None else name
        self.task = None
        self.wake_up = False
        
@dataclass
class _LoopInfo:
    task: asyncio.Task = None
    errormessage: str = ""
