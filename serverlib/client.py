import atexit, sys, signal, readline, zmq, zmq.asyncio, pickle, tabulate, a107, time, serverlib as sl, os, textwrap, re, pl3
from colored import fg, bg, attr
from contextlib import redirect_stdout

__all__ = ["Client", "ServerError", "Retry", "print_result"]

tabulate.PRESERVE_WHITESPACE = True  # Allows me to create a nicer "Summarize2()" table

TIMEOUT = 30000  # miliseconds to wait until server replies
COLOR_OKGREEN = fg("green")
COLOR_FAIL = fg("red")
COLOR_ERROR = fg("light_red")
COLOR_FROM_SERVER = fg("black")+bg("dark_red_2")
COLOR_HAPPY = fg("light_green")
COLOR_SAD = fg("blue")
COLOR_INPUT = fg("orange_1")
COLOR_HEADER = fg("white")

# Client states
CST_INIT = 0     # still in __init__()
CST_ALIVE = 10    # passed __init__()
CST_INITEDCMD = 20  # inited commands
CST_LOOP = 30       # looping in command-line interface
CST_STOPPED = 40    # stopped

POSTHELP = """In addition, output can be directed to a file by using the always-available argument syntax:

   >>>filename
"""

class Client(sl.WithCommands):
    """Client class."""

    @property
    def state(self):
        return self.__state

    @property
    def logger(self):
        return self.cfg.logger

    @property
    def socket(self):
        if self.__ctx is None:
            self.__make_context()
        if self.__socket is None:
            self.__make_socket()
        return self.__socket

    def __init__(self, cfg, cmd=None):
        super().__init__()
        self.__state = CST_INIT
        self.cfg = cfg
        self.flag_needs_to_reset_colors = False
        if cmd is not None: self._attach_cmd(cmd)
        self.__ctx, self.__socket = None, None
        self.__outputfilename = None
        self.__state = CST_ALIVE

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.__close()

    async def connect(self):
        await self.__assure_initialized_cmd()
        _ = self.socket

    async def close(self):
        self.__close()

    async def execute(self, statement, *args, **kwargs):
        """Executes statemen; tries special, then client-side, then server-side."""
        await self.__assure_initialized_cmd()
        statementdata = self.__parse_statement(statement, *args, **kwargs)
        ret, flag = await self.__execute_client_special(statementdata)
        if not flag:
            flag_try_server = False
            try: ret = await self.__execute_client(statementdata)
            except NotAClientCommand: flag_try_server = True
            if flag_try_server: ret = await self.__execute_server(statementdata)
        return ret

    async def execute_client(self, statement, *args, **kwargs):
        """Executes statement; tries special, then client-side."""
        await self.__assure_initialized_cmd()
        statementdata = self.__parse_statement(statement, *args, **kwargs)
        ret, flag = await self.__execute_client_special(statementdata)
        if not flag:
            ret = await self.__execute_client(statementdata)
        return ret

    async def execute_server(self, statement, *args, **kwargs):
        """Executes statement directly on the server."""
        assert isinstance(statement, str)
        await self.__assure_initialized_cmd()
        statementdata = self.__parse_statement(statement, *args, **kwargs)
        return await self.__execute_server(statementdata)
    
    async def execute_bytes(self, bst):
        """Sents statement to server, receives reply, unpickles and returns.

        Args:
            bst: bytes in the form "<command> <data>".

        Returns:
            ret: either result or exception raised on the server (does not raise)
        """
        await self.__assure_initialized_cmd()
        try:
            await self.socket.send(bst)
            b = await self.socket.recv()
        except zmq.Again as e:
            # Will re-create socket in case of timeout
            # https://stackoverflow.com/questions/41009900/python-zmq-operation-cannot-be-accomplished-in-current-state
            self.__del_socket()
            raise Retry(a107.str_exc(e))
        ret = self.__process_result(b)
        return ret

    async def run(self):
        """Will run client and automatically exit the program. Intercepts Ctrl+C and Ctrl+Z."""
        await self.__assure_initialized_cmd()
        self.__intercept_exit()
        self.__set_historylength()
        print(await self.execute_server("_get_welcome"))  # Retrieves and prints welcome message from server
        srvprefix = await self.execute_server("_get_prefix") # Gets server name in order to compose local prompt
        self.__state = CST_LOOP
        try:
            while True:
                self.flag_needs_to_reset_colors = True
                st = input("{}{}{}>".format(COLOR_INPUT, attr("bold"), srvprefix))
                print(attr("reset"), end="")
                self.flag_needs_to_reset_colors = False

                if not st: pass
                elif st == "exit": break
                else: await self.__execute_in_loop(st)
        except KeyboardInterrupt:
            pass
        finally:
            self.__state = CST_STOPPED

    # PRIVATE

    def __parse_statement(self, statement, *args, **kwargs):
        commandname, args, kwargs, self.__outputfilename = sl.parse_statement(statement, *args, **kwargs)
        return commandname, args, kwargs
    
    async def __assure_initialized_cmd(self):
        if self.__state < CST_INITEDCMD: 
            await self._initialize_cmd()
            self.__state = CST_INITEDCMD

    async def __execute_server(self, statementdata):
        commandname, args, kwargs = statementdata
        bst = commandname.encode()+b" "+pickle.dumps([args, kwargs])
        return await self.execute_bytes(bst)

    async def __execute_client(self, statementdata):
        commandname, args, kwargs = statementdata
        if not commandname in self.metacommands: raise NotAClientCommand(f"Not a client command: '{commandname}'")
        method = self.metacommands[commandname].method
        ret = await method(*args, **kwargs)
        return ret

    async def __execute_client_special(self, statementdata):
        commandname, args, kwargs = statementdata
        ret, flag = None, False
        if commandname == "?":
            flag, ret = True, await self.__clienthelp(*args, **kwargs)
        return ret, flag

    async def __execute_in_loop(self, st):
        """Executes and prints result."""
        from serverlib.server import CommandError
        try:
            ret = await self.execute(st)
        except CommandError as e:
            # Here we treat specific exceptions raised by the server
            yoda("Try not -- do it you must.", False)
            my_print_exception(e)
        except Exception as e:
            yoda("Try not -- do it you must.", False)
            my_print_exception(e)
            if hasattr(e, "from_server"): pass
            else:
                a107.log_exception_as_info(self.logger, e, f"Error executing statement '{st}'\n")
        else:
            self.__print_result(ret)

    def __intercept_exit(self):
        # This one gets called at Ctrl+C, but ...
        def _atexit():
            a107.ensure_path(os.path.split(self.cfg.historypath)[0])
            readline.write_history_file(self.cfg.historypath)
            self.__close()
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

    def __make_socket(self):
        self.__del_socket()
        self.__socket = self.__ctx.socket(zmq.REQ)
        self.__socket.setsockopt(zmq.SNDTIMEO, TIMEOUT)
        self.__socket.setsockopt(zmq.RCVTIMEO, TIMEOUT)
        print(f"Connecting ``{self.cfg.prefix}(client)'' to {self.cfg.url} ...")
        self.__socket.connect(self.cfg.url)

    def __make_context(self):
        self.__ctx = zmq.asyncio.Context()

    def __process_result(self, b):
        ret = pickle.loads(b)
        if isinstance(ret, Exception):
            ret.from_server = True
            # e = ret.__class__(f"Error from server: {a107.fancilyquoted(str(ret))}")
            raise ret
        return ret

    def __close(self):
        if self.__socket is not None:
            self.__del_socket()
            self.__ctx.destroy()

    def __del_socket(self):
        if self.__socket is not None:
            try:
                self.__socket.setsockopt(zmq.LINGER, 0)
                self.__socket.close()
            except zmq.ZMQError as e:
                raise
            self.__socket = None

    async def __clienthelp(self, what=None, *args, **kwargs):
            if not what:
                helpdata = await self.execute_server("_help")
                clientgroups = sl.make_groups(self.cmd)
                specialgroup = sl.HelpGroup(title="Client-side specials", items=[
                    sl.HelpItem("?", "complete help"),
                    sl.HelpItem("exit", "exit client"),
                    sl.HelpItem("... >>>filename", "redirects output to file"),])
                helpdata.groups = [specialgroup]+clientgroups+helpdata.groups

                text = sl.make_text(helpdata)
                return text
            else:
                # if what not in self.metacommands:
                #     raise ValueError("Invalid method: '{}'. Use '?' to list client-side methods.".format(what))
                if what in self.metacommands:
                    return sl.format_method(self.metacommands[what].method)
                return await self.execute_server("_help", what)

    def __print_result(self, ret):
        def do_print(flag_colors):
            print_result(ret, self.logger, flag_colors)

        if self.__outputfilename:
            yoda(f"To file '{self.__outputfilename}' output written will be.", True)
            with open(self.__outputfilename, 'w') as f:
                with redirect_stdout(f):
                    do_print(False)
        else:
            yoda("Strong in you the force is.", True)
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


class NotAClientCommand(Exception):
    pass


class ServerError(Exception): pass


class Retry(Exception):
    """Attempt to unify my network error reporting to users of this library (inspired in zmq.Again)."""
    def __init__(self, *args, waittime=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Use to hint how much time should pass before retrying
        self.waittime = waittime if waittime is not None else sl.waittime_retry


_powertabulatemap = [
    {"fieldnames": ("whenthis", "ts", "ts0", "ts1", "nexttime", "whenthisenter", "whenthisexit"),
     "converter": lambda x: a107.dt2str(a107.to_datetime(x)),},
     # "converter": lambda x: a107.ts2str(x, tz=a107.utc)},
    {"fieldnames": ("period",),
     "converter": pl3.QP.to_str},
    {"fieldnames": ("error", "lasterror",),
     "converter": lambda x: "\n".join(textwrap.wrap(x, 50))},
    {"fieldnames": ("narration",),
     "converter": lambda x: "\n".join(textwrap.wrap(x, 50))},
]


def _powertabulate(rows, header, logger=None, *args, **kwargs):
    def get_logger():
        return logger if logger is not None else a107.get_python_logger()
    mymap = [[[i for i, h in enumerate(header) if h in row["fieldnames"]], row["converter"]] for row in _powertabulatemap]
    mymap = [row for row in mymap if row[0]]
    if mymap:
        for row in rows:
            for indexes, converter in mymap:
                for i in indexes:
                    try:
                        if row[i] is not None: row[i] = converter(row[i])
                    except Exception as e:
                        get_logger().info(f"Error '{a107.str_exc(e)}' while trying to apply convertion to field '{header[i]}' with value {repr(row[i])}")
                        raise

    return tabulate.tabulate(rows, header, *args, floatfmt="f", **kwargs)


def _detect_girafales(s):
    lines = s.split("\n")
    return any(line.startswith("-") and line.count("-") > len(line)/2 for line in lines)


def print_result(ret, logger=None, flag_colors=True):
    print_tabulated = a107.print_girafales if flag_colors else print

    def print_header(k, level):
        print(attr('bold')+COLOR_HEADER+"\n".join(a107.format_h(level+1, k))+attr("reset"))

    def handle_list(arg):
        if len(arg) > 0:
            if isinstance(arg[0], dict):
                excluded = ("info",)
                header = [k for k in arg[0].keys() if k not in excluded]
                rows = [[v for k, v in row.items() if k not in excluded] for row in arg]
                print_tabulated(_powertabulate(rows, header))
            else: print("\n".join([str(x) for x in arg]))  # Experimental: join list elements with "\n"
        else: handle_default(arg)

    def handle_dict(arg, level=0):
        if len(arg) > 0:
            first = next(iter(arg.values()))
            if isinstance(first, dict):
                # dict of dicts: converts key to column
                rows = [[k, *v.values()] for k, v in arg.items()]; header = ["key", *first.keys()]
                print_tabulated(_powertabulate(rows, header, logger=logger))
            elif isinstance(first, (tuple, list)):
                # dict of lists: prints keys as titles and processes lists
                for i, (k, v) in enumerate(arg.items()):
                    if i > 0: print()
                    print_header(k, level)
                    handle_list(v)
            elif isinstance(first, str) and "\n" in first:
                # dict of strings with more than one line: prints keys as titles and prints strings
                for i, (k, v) in enumerate(arg.items()):
                    if i > 0: print()
                    print_header(k, level)
                    print(v)
            else:
                # "simple dict": 2-column (key, value) tabloe
                rows = [(k, v) for k, v in arg.items()]; header = ["key", "value"]
                print_tabulated(_powertabulate(rows, header, logger=logger))

        else: handle_default(arg)

    def handle_helpdata(arg):
        text = sl.make_text(arg)
        print(text)

    def handle_default(arg):
        if not isinstance(arg, str): arg = str(arg)
        if "\n" in arg:
            if _detect_girafales(arg): print_tabulated(arg)
            else: print(arg)
        else:
            arg = re.sub(r'\s+', ' ', arg)
            print("\n".join(textwrap.wrap(arg, 80)))

    if isinstance(ret, str): print(ret)
    elif isinstance(ret, tuple) and len(ret) == 2 and isinstance(ret[0], list) and isinstance(ret[1], list):
        # Tries to detect "tabulate-like" (rows, headers) arguments
        print_tabulated(_powertabulate(*ret))
    elif isinstance(ret, list): handle_list(ret)
    elif isinstance(ret, dict): handle_dict(ret)
    elif isinstance(ret, sl.HelpData): handle_helpdata(ret)
    else: handle_default(ret)
