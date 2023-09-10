"""Server, ServerCommands etc."""

__all__ = ["Server"]


import pickle, signal, asyncio, a107, zmq, zmq.asyncio, serverlib as sl, traceback, random, inspect
from colored import attr
from dataclasses import dataclass
from typing import Any
from enum import Enum
import tabulate
from serverlib import config
from . import _api


# Server states
class ServerState(Enum):
    INIT = 0      # still in __init__()
    ALIVE = 10    # passed __init__()
    LOOP = 30     # in main loop
    STOPPED = 40  # stopped


class Server(_api.WithCfg, _api.WithCommands, _api.WithClosers, _api.WithSleepers):
    """Server class.

    Args:
        cfg: ServerConfig
        cmd: instance or list of Servercommands
    """

    whatami = "server"

    @property
    def state(self):
        return self.__state

    @property
    def loops(self):
        return self.__loops

    @property
    def url(self):
        return sl.hopo2url((self.cfg.host, self.cfg.port))

    def __init__(self, cfg, description=None, cmd=None, subservers=None):
        assert issubclass(cfg, sl.ServerCfg)

        _api.WithCfg.__init__(self, cfg, description)
        _api.WithCommands.__init__(self, [sl.BasicServerCommands(), cmd])
        _api.WithClosers.__init__(self)
        _api.WithSleepers.__init__(self)


        self.__state = ServerState.INIT
        self.__loops = None  # {methodname0: task0, ...}
        self.__subservers = _get_scpairs(subservers)
        self.__state = ServerState.ALIVE

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # ┌─┐┬  ┬┌─┐┬─┐┬─┐┬┌┬┐┌─┐  ┌┬┐┌─┐
    # │ │└┐┌┘├┤ ├┬┘├┬┘│ ││├┤   │││├┤
    # └─┘ └┘ └─┘┴└─┴└─┴─┴┘└─┘  ┴ ┴└─┘

    async def _on_initialize(self):
        pass

    async def _on_getd_all(self, statedict):
        """Override this to add elements to statedict in response to server command "s_getd_all"."""

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # ┬ ┬┌─┐┌─┐  ┌┬┐┌─┐
    # │ │└─┐├┤   │││├┤
    # └─┘└─┘└─┘  ┴ ┴└─┘

    async def run(self):
        """
        Runs server

        Returns:
            flag_no_exception: whether the server completed running successfully without an exception being raised
                               inside it

        This method does not raise exception, as the server puts a lot of effort into logging already. It returns
        True/False instead, as explained in "Returns".
        """
        await self._run(0)

    def get_welcome(self):
        """Console welcome message."""
        slugtitle = f"Welcome to the '{self.subappname}' {self.whatami}"
        ret = "\n".join(a107.format_slug(slugtitle, random.randint(0, 2)))
        description = self.description
        if description:
            ret += "\n"+a107.kebab(description, config.descriptionwidth)
        return ret

    def stop(self):
        """Stops server by cancelling all tasks in self.__loops"""
        if self.__loops is not None:
            for loopdata in self.__loops:
                if not loopdata.marked:
                    loopdata.marked = True
                    # print(f"stop() cancelling {task}")
                    loopdata.task.cancel()

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # ┬  ┌─┐┌─┐┬  ┬┌─┐  ┌┬┐┌─┐  ┌─┐┬  ┌─┐┌┐┌┌─┐
    # │  ├┤ ├─┤└┐┌┘├┤   │││├┤   ├─┤│  │ ││││├┤
    # ┴─┘└─┘┴ ┴ └┘ └─┘  ┴ ┴└─┘  ┴ ┴┴─┘└─┘┘└┘└─┘

    async def _run(self, level):
        """
        Recursive run with level.

        Q: Why not __run()?
        A: This method is called by "superserver".
        """

        #########
        # RUN API

        def get_tabulatedloops():
            return [f"    {x}" for x in tabulate.tabulate([loopdata.to_dict() for loopdata in self.__loops],
                                                          "keys").split("\n")]

        async def loopcoro(loopdata):
            """
            Envelope around a server loop or subserver run

            Returns:
                either the result of the method or an exception that was raised
            """

            coro = loopdata.coroutine
            # If subserver, increments level
            awaitable = coro(level + 1) if loopdata.kind != "own loop" else coro()
            try:
                if not loopdata.is_mainloop:
                    # other loops wait until main loop is ready
                    while self.state != ServerState.LOOP:
                        await asyncio.sleep(0.01)
                return await awaitable
            # todo still don't know what to do with keyboard interruption (if ever happens, because it seems that asyncio throws a CancelledError)
            #  except KeyboardInterrupt:
            #     loopdata.flag_interrupted = True
            except asyncio.CancelledError:
                raise
            except BaseException as e:
                # === CRASH

                loopdata.exception = e

                if isinstance(e, zmq.ZMQError) and "Address already in use" in str(e):
                    # It is now worth making a mess because of this
                    raise

                # === LOGGING (crash log)
                self.logger.error(f"💥 {loopdata.detail} **crashed**!")
                self.logger.error("")
                for s in get_tabulatedloops():
                    self.logger.error(s)
                self.logger.error("")
                self.logger.exception(f"Cause of crash follows.")

                raise

        def create_loopdata(method=None, scpair=None):
            loopdata = _LoopData(master=self, method=method, scpair=scpair)
            loopdata.task = asyncio.create_task(loopcoro(loopdata), name=loopdata.detail)
            return loopdata

        # === CREATES LOOPDATA, INCLUDING ASYNC TASKS
        self.__loops = []
        for method in [x[1] for x in inspect.getmembers(self, predicate=inspect.ismethod)
                       if hasattr(x[1], "is_loop") and x[1].is_loop]:
            self.__loops.append(create_loopdata(method=method))
        for scpair in self.__subservers:
            self.__loops.append(create_loopdata(scpair=scpair))

        try:
            await asyncio.gather(
                *[loopdata.task for loopdata in self.__loops],
                return_exceptions=False,  # if any loop crashes the whole server crashes
            )
        except BaseException as e:
            self.logger.error(f"🔥 {self.subappname} (level {level}) ended with exception: {a107.str_exc(e)}")
            if level > 0:
                # Exceptions are propagated until level 0 and then suppressed
                raise
            return False

        # === LOGGING
        self.logger.debug(f"*** Server {self.cfg.subappname} finished execution ***")
        for s in get_tabulatedloops():
            self.logger.debug(s)

        return True

    @sl.is_loop
    async def __mainloop(self):
        async def execute_command(method, data):
            """(callable, list) --> (result or exception) (only raises BaseException)."""

            try:
                if inspect.iscoroutinefunction(method):
                    ret = await method(*data[0], **data[1])
                else:
                    ret = method(*data[0], **data[1])
            except BaseException as e:
                self.logger.exception(f"Error executing '{method.__name__}'")
                # 2023 todo cleanup I think this is too much innovation when Python has a logging framework
                # if sl.config.flag_log_traceback:
                #     a107.log_exception_as_info(self.logger, e, f"Error executing '{method.__name__}'")
                # else:
                #     self.logger.info(f"Error executing '{method.__name__}': {a107.str_exc(e)}")
                ret = e
            return ret

        def parse_statement(st):
            """bytes --> (commandname, has_data, data, command, exception) (str, bool, bytes, callable, StatementError/None)."""
            bdata, data, command, exception = b"", [], None, None
            # Splits statement
            try:
                idx = st.index(b" ")
            except ValueError:
                commandname = st.decode()
            else:
                commandname, bdata = st[:idx].decode(), st[idx+1:]
            has_data = len(bdata) > 0
            # Figures out method
            try:
                command = self.metacommands[commandname]
            except KeyError:
                message = f"Command is non-existing: '{commandname}'"
                self.logger.info(message)
                exception = sl.StatementError(message)
            else:
                self.logger.info(f"$ {commandname}{' ...' if has_data else ''}")
            # Processes data
            if command:
                data = [[], {}] if len(bdata) == 0 else [[bdata], {}] if command.flag_bargs else pickle.loads(bdata)
                if not isinstance(data, list):
                    exception = sl.StatementError(f"Data must unpickle to a [args, kwargs], not a {data.__class__.__name__}")
                elif len(data) != 2 or type(data[0]) not in (list, tuple) or type(data[1]) != dict:
                    exception = sl.StatementError("Data must unpickle to [args, kwargs]")
            return commandname, has_data, data, command, exception

        async def recv_send():
            try:
                st = await sck_rep.recv()
                commandname, has_data, data, command, exception = parse_statement(st)
                if exception:
                    result = exception
                else:
                    result = await execute_command(command.method, data)

                try:
                    msg = pickle.dumps(result)
                except BaseException as e:
                    self.logger.exception("Error pickling result")
                    # # 2023 todo cleanup I think this is too much innovation when Python has a logging framework
                    # if sl.config.flag_log_traceback:
                    #     a107.log_exception_as_info(self.logger, e, f"Error pickling result")
                    # else:
                    #     self.logger.info(f"Error pickling result: {a107.str_exc(e)}")

                    msg = pickle.dumps(e)
                    await sck_rep.send(msg)
                else:
                    await sck_rep.send(msg)

            except zmq.Again:
                return False
            return True

        def _ctrl_z_handler(signum, frame):
            print("Don't press Ctrl+Z 😠, or clean-up code won't be executed 😱; Ctl+C should do thou 😜")

        try:
            # === INITIALIZATION
            signal.signal(signal.SIGTSTP, _ctrl_z_handler)
            signal.signal(signal.SIGTERM, _ctrl_z_handler)

            self.read_configfile()
            if a107.ensure_path(self.datadir):
                self.logger.info(f"Created directory '{self.datadir}'")
            ctx = zmq.asyncio.Context()
            sl.lowstate.numcontexts += 1
            sck_rep = ctx.socket(zmq.REP)
            sl.lowstate.numsockets += 1

            # === BINDING
            try:
                self.logger.info(f"Binding ``{self.subappname}'' (REP) to {self.url} at {a107.now_str()} ...")
                sck_rep.bind(self.url)
            except zmq.ZMQError as e:
                self.logger.error(f"Cannot bind to {self.url}: {a107.str_exc(e)}")
                raise

            await self._initialize_cmd()
            # todo not yet, if ever ... await self.__start_subservers()
            await self._on_initialize()
            # MAIN LOOP ...
            self.__state = ServerState.LOOP
            try:
                while True:
                    did_sth = await recv_send()
                    if not did_sth:
                        # Sleeps because tired of doing nothing
                        if self.sleepinterval > 0:
                            await asyncio.sleep(self.sleepinterval)
            except asyncio.CancelledError:
                raise
            # except KeyboardInterrupt:
            #     return "⌨ K ⌨ E ⌨ Y ⌨ B ⌨ O ⌨ A ⌨ R ⌨ D ⌨"
            # except:
            #     self.logger.exception(f"Server '{self.subappname}' ☠C☠R☠A☠S☠H☠E☠D☠")
            #     raise
            finally:
                self.__state = ServerState.STOPPED
                self.logger.debug(f"{self.__class__.__name__}.__mainloop() finally'")
                self.wake_up()

                # Thought I might wait a bit before cancelling all loops (to let them do their shit; might reduce probability of errors)
                await asyncio.sleep(0.1)
                self.stop()
                await self.close()

                sck_rep.close()
                sl.lowstate.numsockets -= 1
                ctx.destroy()
                sl.lowstate.numcontexts -= 1
        finally:
            self.logger.info(f"Exiting {self.__class__.__name__}.__mainloop()")


def _get_scpairs(scpairs):
    if not scpairs:
        return []

    if isinstance(scpairs, sl.SCPair):
        return [scpairs]

    ret = []
    for i, item in enumerate(scpairs):
        if isinstance(item, sl.SCPair):
            ret.append(item)
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            ret.append(sl.SCPair(*item))
        else:
            raise ValueError(f"Cannot convert item #{i} to serverlib.SCPair")
    return ret

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

@dataclass
class _LoopData:
    """Encapsulates a @sl.is_loop-decorated method or a sub-server."""

    def __str__(self):
        return self.methodname

    @property
    def methodname(self):
        return self.method.__name__ if self.kind == "own loop" else None

    @property
    def flag_error(self):
        return self.exception is not None

    @property
    def errormessage(self):
        if self.exception is None:
            return ""
        return a107.str_exc(self.exception)

    @property
    def taskstatus(self):
        return "no task" if self.task is None \
            else "looping" if not self.task.done() \
            else "cancelled" if self.task.cancelled() \
            else "completed"

    @property
    def kind(self):
        return "own loop" if self.method else "subserver"

    @property
    def detail(self):
        ret = f"{self.master.__class__.__name__}.{self.methodname}()" if self.kind == "own loop" \
            else f"{self.scpair.server.__class__.__name__}.run()"
        return ret

    @property
    def coroutine(self):
        return self.method if self.kind == "own loop" else self.scpair.server._run

    @property
    def is_mainloop(self):
        return self.kind == "own loop" and self.methodname.endswith("__mainloop")

    # reference to the server
    master: Any
    # awaitable method with the @is_loop decorator. It has precedence over scpair
    method: Any = None
    # awaitable method with the @is_loop decorator
    scpair: sl.SCPair = None
    # asyncio.Task
    task: Any = None
    # exception in case of error
    exception: BaseException = None
    # marked to die, like Guts
    marked: bool = False
    # method result after awaited on
    result: Any = None

    # todo cleanup when I am sure this is no longer an idea to be implemented # whether task was interrupted with KeyboardInterrupt
    #  flag_interrupted = False

    def to_dict(self):
        return {"kind": self.kind,
                "detail": self.detail,
                "taskstatus": self.taskstatus,
                "marked": self.marked,
                "errormessage": self.errormessage,
                ";)": "💥" if self.errormessage else "",
                # ";)": "^C" if self.flag_interrupted else "💥" if self.errormessage else "",
                }
