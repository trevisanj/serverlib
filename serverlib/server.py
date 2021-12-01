"""Server, ServerCommands etc."""

__all__ = ["Server", "ST_INIT", "ST_ALIVE", "ST_LOOP", "ST_STOPPED"]

import pickle, os, signal, asyncio, random, a107, zmq, zmq.asyncio, serverlib as sl, traceback, random
from colored import fg, bg, attr
from .basicservercommands import *


# Server states
ST_INIT = 0     # still in __init__()
ST_ALIVE = 10    # passed __init__()
ST_LOOP = 30     # in main loop
ST_STOPPED = 40  # stopped


class Server(sl.WithCommands, sl.WithClosers, sl.WithSleepers):
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
    def lo_ops(self):
        return self.__lo_ops

    def __init__(self, cfg, cmd=None, flag_basiccommands=True):
        sl.WithCommands.__init__(self)
        sl.WithClosers.__init__(self)
        sl.WithSleepers.__init__(self)
        self.__state = ST_INIT
        self.cfg = cfg
        cfg.master = self
        self.__lo_ops = None  # {methodname:
        self._attach_cmd(_EssentialServerCommands())
        if flag_basiccommands: self._attach_cmd(BasicServerCommands())
        if cmd is not None: self._attach_cmd(cmd)
        self.__state = ST_ALIVE

    # ┌─┐┬  ┬┌─┐┬─┐┬─┐┬┌┬┐┌─┐  ┌┬┐┌─┐
    # │ │└┐┌┘├┤ ├┬┘├┬┘│ ││├┤   │││├┤
    # └─┘ └┘ └─┘┴└─┴└─┴─┴┘└─┘  ┴ ┴└─┘

    async def _on_initialize(self): pass

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
                middles = [f"Crash in {self.__class__.__name__}.{attrname}()", "Loops and errors:"]
                middles.extend([f"  {'🦓' if v.errormessage else '🐱'} {k}: {v.errormessage}" for k, v in self.__lo_ops.items()])
                for s in middles:
                    print(f"🐛🐛🐛 {attr('bold')}{s}{attr('reset')}")
                traceback.print_exc()
                raise

        def create_task(attrname):
            task = asyncio.create_task(loopcoro(attrname), name=attrname)
            task.errormessage = None
            task.marked = False  # marked to die, like Guts
            return task

        self.__lo_ops = {attrname: create_task(attrname) for attrname in attrnames}
        results = await asyncio.gather(*self.__lo_ops.values(), return_exceptions=True)
        self.logger.debug(f"*** Server {self.cfg.subappname} -- how the story ended: ***")
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
            """bytes --> (commandname, has_data, data, command, exception) (str, bool, bytes, callable, StatementError/None)."""
            bdata, data, command, exception = b"", [], None, None
            # Splits statement
            try: idx = st.index(b" ")
            except ValueError: commandname = st.decode()
            else: commandname, bdata = st[:idx].decode(), st[idx+1:]
            has_data = len(bdata) > 0
            # Figures out method
            try: command = self.metacommands[commandname]
            except KeyError:
                message = f"Command is non-existing: '{commandname}'"
                self.logger.info(message)
                exception = sl.StatementError(message)
            else: self.cfg.logger.info(f"$ {commandname}{' ...' if has_data else ''}")
            # Processes data
            if command:
                data = [[], {}] if len(bdata) == 0 else [[bdata], {}] if command.flag_bargs else pickle.loads(bdata)
                if not isinstance(data, list):
                    exception = sl.StatementError(f"Data must unpickle to a list, not a {data.__class__.__name__}")
                elif len(data) != 2 or type(data[0]) not in (list, tuple) or type(data[1]) != dict:
                    exception = sl.StatementError("Data must unpickle to a structure like this: [[...], {...}]")
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
        sl.lowstate.numcontexts += 1
        sck_rep = ctx.socket(zmq.REP)
        sl.lowstate.numsockets += 1
        logmsg = f"Binding ``{self.cfg.subappname}'' (REP) to {self.cfg.url} ..."
        self.cfg.logger.info(logmsg)
        if not self.cfg.flag_log_console: print(logmsg) # If not logging to console, prints sth anyway (helps a lot)
        sck_rep.bind(self.cfg.url)
        await self._initialize_cmd()
        await self._on_initialize()
        # MAIN LOOP ...
        self.__state = ST_LOOP
        try:
            while True:
                did_sth = await recv_send()
                if not did_sth:
                    # Sleeps because tired of doing nothing
                    if self.cfg.sleepinterval > 0: await asyncio.sleep(self.cfg.sleepinterval)
        except asyncio.CancelledError: raise
        except KeyboardInterrupt: return "⌨ K ⌨ E ⌨ Y ⌨ B ⌨ O ⌨ A ⌨ R ⌨ D ⌨"
        except:
            self.cfg.logger.exception(f"Server '{self.cfg.subappname}' ☠C☠R☠A☠S☠H☠E☠D☠")
            raise
        finally:
            self.__state = ST_STOPPED
            self.cfg.logger.debug(f"😀 DON'T WORRY 😀 {self.__class__.__name__}.__serverloop() 'finally:'")
            self.wake_up()
            await asyncio.sleep(0.1); self.stop()  # Thought I might wait a bit before cancelling all loops (to let them do their shit; might reduce probability of errors)
            await self.close()
            sck_rep.close()
            sl.lowstate.numsockets -= 1
            ctx.destroy()
            sl.lowstate.numcontexts -= 1


class _EssentialServerCommands(sl.ServerCommands):
    async def _get_welcome(self):
        return self.master.cfg.get_welcome()

    async def _get_name(self):
        """Returns the server application name."""
        return self.cfg.appname

    async def _get_subappname(self):
        """Returns the server subappname."""
        return self.cfg.subappname

    async def _get_prompt(self):
        """Returns what the server thinks that should be the client prompt."""
        return self.cfg.subappname

    async def _poke(self):
        """Prints and returns the server subappname (useful to identify what is running in a terminal)."""
        # print(f"👉 {self.cfg.subappname}")  # 👈")
        print(f"{fg('white')}{attr('bold')}{self.cfg.subappname}{attr('reset')} 👈")
        return self.cfg.subappname

    async def _help(self, what=None, flag_docstrings=False, refilter=None, fav=None, favonly=False):
        """Gets summary of available server commands or help on specific command.

        Args:
            what: specific command
            flag_docstrings: whether to include docstrings in help data
            refilter: regular expression. If passed, will filter commands containing this expression
            fav: favourites list
            favonly: flag, whether to include only favourite items
        """
        if what is None:
            cfg = self.master.cfg
            helpdata = sl.make_helpdata(title=cfg.subappname,
                                        description=cfg.description,
                                        cmd=self.master.cmd,
                                        flag_protected=True,
                                        flag_docstrings=flag_docstrings,
                                        refilter=refilter,
                                        fav=fav,
                                        favonly=favonly)
            return helpdata
        else:
            if what not in self.master.metacommands:
                raise ValueError("Invalid method: '{}'".format(what))
            return sl.format_method(self.master.metacommands[what].method)

