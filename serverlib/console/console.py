__all__ = ["Console"]

import atexit, sys, signal, readline, tabulate, a107, time, serverlib as sl, os
from contextlib import redirect_stdout
from colored import attr

from serverlib import _api
from serverlib.config import *
from . import _capi
from ._capi import CST
from ._essentialconsolecommands import EssentialConsoleCommands


# I have to disable this, otherwise any input() result will be automatically added to history.
readline.set_auto_history(False)


class Console(_api.WithCommands, _api.WithClosers):
    """
    Console is the base class for serverlib.Client

    This separates console functionality from the client-server model, allowing for creation of one-sided consoles,
    such as pl3.WDB2Console
    """

    # "console" or "client" (will be set by "client" subclass)
    what = "console"

    @property
    def state(self):
        return self.__state

    @property
    def logger(self):
        return self.cfg.logger

    def __init__(self, cfg, cmd=None):
        _api.WithCommands.__init__(self)
        _api.WithClosers.__init__(self)
        self.__state = CST.INIT
        self.cfg = cfg
        self.flag_needs_to_reset_colors = False
        self._attach_cmd(EssentialConsoleCommands())
        if cmd is not None: self._attach_cmd(cmd)
        self.__state = CST.ALIVE

        self.name = a107.random_name()

    # DATA MODEL

    async def __aenter__(self):
        return self

    async def __aexit__(self, type_, value, traceback):
        if self.__state < CST.CLOSED:
            await self.close()

    # INTERFACE

    async def execute(self, statement, *args, **kwargs):
        if isinstance(statement, bytes):
            raise TypeError("For bytes, use execute_bytes() instead!")
        await self._assure_initialized()
        self._parse_statement(statement, args, kwargs)
        return await self._do_execute()

    def print_last_result(self, result):
        """Uses internal mechanism to print result

        This should be invoked immediately after last command, as it uses the internal state from last command.
        """
        self.__print_result(result)

    async def run(self):
        """Will run console and automatically exit the program. Intercepts Ctrl+C and Ctrl+Z."""

        async def execute_in_loop(st):
            """Executes and prints result."""

            def blueyoda(e):
                _capi.yoda("Try not -- do it you must.", False)
                _capi.my_print_exception(e)

            try:
                result = await self.execute(st)
            except (sl.StatementError, sl.NotAConsoleCommand) as e:
                blueyoda(e)
            except BaseException as e:
                blueyoda(e)
                if hasattr(e, "from_server"):
                    pass
                else:
                    a107.log_exception_as_info(self.logger, e, f"Error executing statement '{st}'\n")
            else:
                self.__print_result(result)

        await self._assure_initialized()
        self.__intercept_exit()
        self.__set_historylength()
        print(await self._get_welcome())
        prompt = await self._get_prompt()
        self.__state = CST.LOOP
        try:
            while True:
                self.flag_needs_to_reset_colors = True
                readline.set_auto_history(True)
                st = input("{}{}{}>".format(config.colors.input, attr("bold"), prompt))
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
            self.__state = CST.STOPPED
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
        self.__state = CST.CLOSED

    # OVERRIDABLE

    async def _on_initialize(self):
        pass

    # OVERRIDED BY Client CLASS ONY

    async def _initialize_client(self):
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

    def _handle_result_for_printing(self, result):
        """Optional feature to convert results into something else

        Return;
           ret, flag_handled
        """
        return None, False

    async def _do_help_what(self, commandname):
        if commandname in self.metacommands:

            return _api.format_method(_api.make_helpitem(self.metacommands[commandname], True, self.cfg.fav))
        raise sl.NotAConsoleCommand(f"Not a {self.what} command: '{commandname}'")

    # PROTECTED (NOT OVERRIDABLE)

    async def _get_help_specialgroup(self):
        """Returns the help "special group"; called by Console and Client."""
        specialgroup = _api.HelpGroup(title="Console specials", items=[
            _api.HelpItem("?", "alias for 'help'"),
            _api.HelpItem("exit", "exit console"),
            _api.HelpItem("... >>>filename", "redirects output to file"), ])
        return specialgroup

    def _parse_statement(self, statement, args, kwargs):
        self._statementdata = _capi.parse_statement(statement, args, kwargs)
        return self._statementdata

    async def _assure_initialized(self):
        if self.__state < CST.INITIALIZED:
            self.cfg.read_configfile()
            await self._initialize_cmd()
            await self._initialize_client()
            await self._on_initialize()
            self.__state = CST.INITIALIZED

    # PRIVATE

    async def _execute_console(self):
        data = self._statementdata
        if not data.commandname in self.metacommands:
            raise sl.NotAConsoleCommand(f"Not a {self.what} command: '{data.commandname}'")
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

    def __print_result(self, result):
        result_, flag_handled = self._handle_result_for_printing(result)
        result__ = result_ if flag_handled else result

        outputfilename = self._statementdata.outputfilename
        if outputfilename:
            _capi.yoda(f"To file '{outputfilename}' output written will be.", True)
            with open(outputfilename, 'w') as f:
                with redirect_stdout(f):
                    sl.print_result(result__, self.logger, flag_colors=False)
        else:
            yodanonsense = "Strong in you the force is."
            if isinstance(result__, sl.Status) and result__.yoda:
                yodanonsense = result__.yoda
            _capi.yoda(yodanonsense, True)
            sl.print_result(result__, self.logger, flag_colors=True)

