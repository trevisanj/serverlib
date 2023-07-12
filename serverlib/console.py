__all__ = ["Console"]

import atexit, sys, signal, readline, tabulate, a107, time, serverlib as sl, os
from dataclasses import dataclass
from typing import List
from contextlib import redirect_stdout
from serverlib.consts import *
from colored import attr
from . import _api

# I have to disable this, otherwise any input() result will be automatically added to history.
readline.set_auto_history(False)

tabulate.PRESERVE_WHITESPACE = True  # Allows me to create a nicer "Summarize2()" table

# Console states
CST_INIT = 0  # still in __init__()
CST_ALIVE = 10  # passed __init__()
CST_INITIALIZED = 20  # inited commands
CST_LOOP = 30  # looping in command-line interface
CST_STOPPED = 40  # stopped
CST_CLOSED = 50

class Console(_api.WithCommands, _api.WithClosers):
    """
    Console is the base class for serverlib.Client

    This separates console functionality from the client-server model, allowing for creation of one-sided consoles,
    such as pl3.WDB2Console
    """

    @property
    def state(self):
        return self.__state

    @property
    def logger(self):
        return self.cfg.logger

    def __init__(self, cfg, cmd=None):
        _api.WithCommands.__init__(self)
        _api.WithClosers.__init__(self)
        self.__state = CST_INIT
        self.cfg = cfg
        self.flag_needs_to_reset_colors = False
        self._attach_cmd(_EssentialConsoleCommands())
        if cmd is not None: self._attach_cmd(cmd)
        self.__outputfilename = None
        self.__state = CST_ALIVE

        self.name = a107.random_name()

    # DATA MODEL

    async def __aenter__(self):
        return self

    async def __aexit__(self, type_, value, traceback):
        if self.__state < CST_CLOSED:
            await self.close()

    # INTERFACE

    async def execute(self, statement, *args, **kwargs):
        if isinstance(statement, bytes):
            raise TypeError("For bytes, use execute_bytes() instead!")
        await self._assure_initialized()
        self._parse_statement(statement, args, kwargs)
        return await self._do_execute()

    async def run(self):
        """Will run client and automatically exit the program. Intercepts Ctrl+C and Ctrl+Z."""

        async def execute_in_loop(st):
            """Executes and prints result."""

            def blueyoda(e):
                yoda("Try not -- do it you must.", False)
                my_print_exception(e)

            try:
                ret = await self.execute(st)
            except (sl.StatementError, sl.NotAClientCommand) as e:
                blueyoda(e)
            except Exception as e:
                blueyoda(e)
                if hasattr(e, "from_server"):
                    pass
                else:
                    a107.log_exception_as_info(self.logger, e, f"Error executing statement '{st}'\n")
            else:
                self.__print_result(ret)


        await self._assure_initialized()
        self.__intercept_exit()
        self.__set_historylength()
        print(await self._get_welcome())
        prompt = await self._get_prompt()
        self.__state = CST_LOOP
        try:
            while True:
                self.flag_needs_to_reset_colors = True
                readline.set_auto_history(True)
                st = input("{}{}{}>".format(COLOR_INPUT, attr("bold"), prompt))
                readline.set_auto_history(False)
                print(attr("reset"), end="")
                self.flag_needs_to_reset_colors = False

                if not st:
                    pass
                elif st == "exit":
                    break
                else:
                    await execute_in_loop(st)
        except KeyboardInterrupt:
            pass
        finally:
            self.__state = CST_STOPPED
            await self.close()

    async def help(self, what=None, favonly=False):
        """Help entry point.

        Args:
            what: may be a command name or may contain wildcards ("*"), e.g. "*draw*".
            favonly: whether to get only favourites

        Returns:
            str
        """
        flag_specific = what and "*" not in what
        if flag_specific:
            return await self._do_help_what(what)
        else:
            refilter = None if what is None else what.replace("*", ".*")
            return await self._do_help(refilter=refilter, fav=self.cfg.fav, favonly=favonly)

    async def close(self):
        await _api.WithClosers.close(self)
        self.__state = CST_CLOSED

    # OVERRIDABLE

    async def _on_initialize(self):
        pass
    
    async def _do_execute(self):
        return await self._execute_console()

    async def _get_prompt(self):
        return self.cfg.subappname

    async def _get_welcome(self):
        return self.cfg.get_welcome()

    async def _do_help(self, refilter=None, fav=None, favonly=False):
        cfg = self.cfg
        helpdata = _api.make_helpdata(title=cfg.subappname,
                                      description=cfg.description,
                                      cmd=self.cmd, flag_protected=True,
                                      refilter=refilter,
                                      fav=fav,
                                      favonly=favonly)
        if not refilter and not favonly:
            specialgroup = await self._get_help_specialgroup()
            helpdata.groups = [specialgroup]+helpdata.groups
        text = _api.make_text(helpdata)
        return text

    def _handle_result(self, result):
        """Optional result handler. Must return (ret, flag_handled)."""
        return None, False

    async def _do_help_what(self, commandname):
        if commandname in self.metacommands:

            return _api.format_method(_api.make_helpitem(self.metacommands[commandname], True, self.cfg.fav))
        raise sl.NotAClientCommand(f"Not a client command: '{commandname}'")

    # PROTECTED (NOT OVERRIDABLE)

    async def _get_help_specialgroup(self):
        """Returns the help "special group"; called by Console and Client."""
        specialgroup = _api.HelpGroup(title="Console specials", items=[
            _api.HelpItem("?", "alias for 'help'"),
            _api.HelpItem("exit", "exit console"),
            _api.HelpItem("... >>>filename", "redirects output to file"), ])
        return specialgroup

    def _parse_statement(self, statement, args, kwargs):
        self._statementdata = _console_parse_statement(statement, args, kwargs)
        return self._statementdata

    async def _assure_initialized(self):
        if self.__state < CST_INITIALIZED:
            self.cfg.read_configfile()
            await self._initialize_cmd()
            await self._on_initialize()
            self.__state = CST_INITIALIZED

    # PRIVATE

    async def _execute_console(self):
        data = self._statementdata
        if not data.commandname in self.metacommands:
            raise sl.NotAClientCommand(f"Not a client command: '{data.commandname}'")
        meta = self.metacommands[data.commandname]
        method = meta.method
        if meta.flag_awaitable:
            ret = await method(*data.args, **data.kwargs)
        else:
            ret = method(*data.args, **data.kwargs)
        return ret

    def __intercept_exit(self):
        # This one gets called at Ctrl+C, but ...
        def _atexit():
            a107.ensure_path(os.path.split(self.cfg.historypath)[0])
            readline.write_history_file(self.cfg.historypath)
            # await self.close()
            if self.flag_needs_to_reset_colors:
                for t, letter in zip((.2, .07, .07, .1), "exit"):
                    print(letter, end="")
                    sys.stdout.flush()
                    time.sleep(t)
                print(attr("reset"))

        # ... we need this to handle the Ctrl+Z.
        def _ctrl_z_handler(signum, frame):
            # this will trigger _atexit()
            sys.exit()

        atexit.register(_atexit)
        signal.signal(signal.SIGTSTP, _ctrl_z_handler)

    def __set_historylength(self):
        """Sets history length. default history len is -1 (infinite), which may grow unruly."""
        try:
            readline.read_history_file(self.cfg.historypath)
        except FileNotFoundError:
            pass
        else:
            readline.set_history_length(1000)

    def __print_result(self, ret):
        def do_print(flag_colors):
            ret_, flag_handled = self._handle_result(ret)
            ret__ = ret_ if flag_handled else ret
            _api.print_result(ret__, self.logger, flag_colors)

        outputfilename = self._statementdata.outputfilename
        if outputfilename:
            yoda(f"To file '{outputfilename}' output written will be.", True)
            with open(outputfilename, 'w') as f:
                with redirect_stdout(f):
                    do_print(False)
        else:
            yodanonsense = "Strong in you the force is."
            if isinstance(ret, sl.Status) and ret.yoda:
                yodanonsense = ret.yoda
            yoda(yodanonsense, True)
            do_print(True)


def yoda(s, happy=True):
    if s.endswith("."): s = s[:-1]+" ·"  # Yoda levitates the period
    print(attr("bold")+(COLOR_HAPPY if happy else COLOR_SAD), end="")
    print("{0}|o_o|{0} -- {1}".format("^" if happy else "v", s), end="")  # ◐◑
    print(attr("reset")*2)


def my_print_exception(e):
    parts = []
    if hasattr(e, "from_server"): parts.append(f'{COLOR_FROM_SERVER}(Error from server){attr("reset")}')
    parts.append(f'{COLOR_ERROR}{attr("bold")}{e.__class__.__name__}:{attr("reset")}')
    parts.append(f'{COLOR_ERROR}{str(e)}{attr("reset")}')
    print(" ".join(parts))



class _EssentialConsoleCommands(sl.ConsoleCommands):
    @sl.is_command
    async def help(self, what=None, favonly=False):
        """Gets general help or help on specific command."""
        return await self.master.help(what, favonly)

    @sl.is_command
    async def favhelp(self, what=None, favonly=False):
        """Equivalent to "help favonly=True"."""
        return await self.help(favonly=True)

    @sl.is_command
    async def fav(self, what):
        """Toggles favourite command."""
        fav = self.master.cfg.fav
        what= str(what).lower()
        if what in fav:
            fav.remove(what)
        else:
            fav.append(what)
        self.master.cfg.set("fav", fav)

    @sl.is_command
    async def get_fav(self):
        """Return list of favourite commands."""
        return self.master.cfg.fav

    @sl.is_command
    async def getd_lowstate(self):
        return sl.lowstate.__dict__


def _console_parse_statement(statement, args_, kwargs_):
    """Parses statement and returns StatementData"""
    statement = statement.lstrip()
    outputfilename = None
    flag_server = False
    try:
        index = statement.index(" ")
    except ValueError:
        commandname, args, kwargs = statement, [], {}
    else:
        commandname = statement[:index]
        args, kwargs = a107.str2args(statement[index+1:])
    if commandname.startswith(">"):
        commandname = commandname[1:]
        flag_server = True
    elif commandname == "?":
        commandname = "help"
    if args_: args.extend(args_)
    if kwargs_: kwargs.update(kwargs_)
    if args:
        if isinstance(args[-1], str) and args[-1].startswith(">>>"):
            outputfilename = args.pop()[3:]
    ret = _StatementData(commandname, args, kwargs, outputfilename, flag_server)
    return ret


@dataclass
class _StatementData:
    commandname: str
    args: List
    kwargs: List
    outputfilename: str
    flag_server: bool


