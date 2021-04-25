"""Server, ServerCommands etc."""
import logging, sys, time, pickle, os, signal, httplib2, asyncio, random, a107, zmq, zmq.asyncio, inspect, copy
from colored import fg, bg, attr
from . import whatever
from .commands import _Commands
__all__ = ["ServerCommands", "Server", "CommandError", "BasicServerCommands",
           "ST_INIT", "ST_ALIVE", "ST_LOOP", "ST_STOPPED"]


class _ServerCommand:
    def __init__(self, method):
        self.method = method
        self.name = method.__name__
        pars = inspect.signature(method).parameters
        flag_bargs = "bargs" in pars
        if flag_bargs and len(pars) > 1:
            raise AssertionError(f"Method {self.name} has argument named 'bargs' which identifies it as a bytes-accepting method, but has extra arguments")
        self.flag_bargs = flag_bargs


class   ServerCommands(_Commands):
    """
    Class that implements all server-side "commands".

    Notes:
        - Subclass this to implement new commands
        - All arguments come as bytes
        - Don't forget to make them all "async"
    """
    name = None
    def __init__(self):
        assert self.name is not None, f"Forgot to set the 'name' class variable for class {self.__class__.__name__}"
        super().__init__()

    @staticmethod
    def to_list(args):
        """Converts bytes to list of strings."""
        return [x for x in args.decode().split(" ") if len(x) > 0]


class _EssentialServerCommands(ServerCommands):
    name = "essential"

    async def _get_welcome(self):
        return "\n".join(a107.format_slug(f"Welcome to the '{self.master.cfg.prefix}' server", random.randint(0, 2)))

    async def _get_name(self):
        """Returns the server application name."""
        return self.cfg.applicationname

    async def _get_prefix(self):
        """Returns the server prefix."""
        return self.cfg.prefix


class BasicServerCommands(ServerCommands):
    name = "basic"
    async def help(self, what=None):
        """Gets summary of available server commands or help on specific command."""
        if what is None:
            name_method = [(k, v.method) for k, v in self.master.commands_by_name.items()]
            aname = self.master.cfg.prefix
            lines = [aname, "="*len(aname)]
            if self.master.cfg.description: lines.extend(whatever.format_description(self.master.cfg.description))
            lines.append("")
            lines.extend(whatever.format_name_method(name_method))
            return "\n".join(lines)
        else:
            if what not in self.master.commands_by_name:
                raise ValueError("Invalid method: '{}'. Use 'help()' to list methods.".format(what))
            return whatever.format_method(self.master.commands_by_name[what].method)

    async def stop(self):
        """Stops server. """
        self.master.stop()
        return "As you wish."

    async def get_configuration(self):
        """Returns dict containing configuration information.

        Returns:
            {script_name0: filepath0, ...}
        """
        return self.master.get_configuration()

    async def ping(self):
        """Returns "pong"."""
        return "pong"


# Server states
ST_INIT = 0     # still in __init__()
ST_ALIVE = 1    # passed __init__()
ST_LOOP = 2     # in main loop
ST_STOPPED = 3  # stopped


class Server(object):
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

    def __init__(self, cfg, cmd=None, flag_basiccommands=True):
        self.__state = ST_INIT
        self.cfg = cfg
        cfg.master = self

        # More init
        self.__logger = None
        self.__flag_to_stop = False # stop at next chance
        self.__recttask = None
        self.__sleeptasks = []
        self.ctx = None  # zmq context
        self.sck_rep = None  # ZMQ_REP socket

        # Commands
        self.cmdcmd = []  # list of ServerCommands objects
        self.cmd_by_name = {}  # {cmd.name: cmd, ...}
        self.commands_by_name = {}  # {commandname: _ServerCommand, ...}, synthesized from all self.cmdcmd
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

    def attach_cmd(self, cmdcmd):
        """Attaches one or more ServerCommands instances."""
        if not isinstance(cmdcmd, (list, tuple)): cmdcmd = [cmdcmd]
        for cmd in cmdcmd: 
            if not isinstance(cmd, ServerCommands): raise TypeError(f"Invalid commands type: {cmd.__class__.__name__}")
        for cmd in cmdcmd:
            cmd.master = self
            self.cmdcmd.append(cmd)
            self.cmd_by_name[cmd.name] = cmd
            for name, method in whatever.get_methods(cmd, flag_protected=True):
                self.commands_by_name[name] = _ServerCommand(method)

    def get_configuration(self):
        """Returns tabulatable (rows, ["key", "value"] self.cfg + additional in-server information."""
        # TODO return as dict, but create a nice visualization at the client side
        _ret = self.cfg.to_dict()
        ret = list(_ret.items()), ["key", "value"]
        return ret

    def wake_up(self):
        """Cancel all "sleepings"."""
        for sleeptask in copy.copy(self.__sleeptasks): sleeptask.cancel()
        self.__sleeptasks = []

    async def sleep(self, to_wait):
        sleeptask = asyncio.create_task(asyncio.sleep(to_wait))
        self.__sleeptasks.append(sleeptask)
        try: await sleeptask
        except asyncio.CancelledError: pass
        finally: self.__sleeptasks.remove(sleeptask)

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
        gathered = [getattr(self, attrname)() for attrname in attrnames]
        await asyncio.gather(*gathered)

    # ┬  ┌─┐┌─┐┬  ┬┌─┐  ┌┬┐┌─┐  ┌─┐┬  ┌─┐┌┐┌┌─┐
    # │  ├┤ ├─┤└┐┌┘├┤   │││├┤   ├─┤│  │ ││││├┤
    # ┴─┘└─┘┴ ┴ └┘ └─┘  ┴ ┴└─┘  ┴ ┴┴─┘└─┘┘└┘└─┘

    async def __serverloop(self):
        a107.ensurepath(self.cfg.datadir)
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
                        # print("I ACTUALLY DID SUM SHIT")
                except KeyboardInterrupt:
                    self.__stop()
        except:
            self.cfg.logger.exception(f"Server '{self.cfg.prefix}' crashed!")
            raise
        finally:
            self.cfg.logger.debug(f"{self.__class__.__name__}.__serverloop() finalliessssssssssssssssssssssssss")
            self.wake_up()
            self.__state = ST_STOPPED
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

    # TODO this is getting outdated, or I should cancel the send_recv() task, because it is currently blocking *for a long time*, so the main loop won't detect this soon.
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
            elif len(data) != 2 or type(data[0]) != list or type(data[1]) != dict:
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