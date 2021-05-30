import atexit, sys, signal, readline, zmq, zmq.asyncio, pickle, tabulate, a107, time, serverlib as sl, os, textwrap, re, pl3
from colored import fg, attr

__all__ = ["Client", "ServerError", "TryAgain", "print_result"]

tabulate.PRESERVE_WHITESPACE = True  # Allows me to create a nicer "Summarize2()" table

TIMEOUT = 30000  # miliseconds to wait until server replies
COLOR_OKGREEN = fg("green")
COLOR_FAIL = fg("red")
COLOR_ERROR = fg("light_red")
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
        statementdata = sl.parse_statement(statement, *args, **kwargs)
        ret, flag = await self.__execute_client_special(statementdata)
        if not flag:
            try: ret = await self.__execute_client(statementdata)
            except NotAClientCommand: ret = await self.__execute_server(statementdata)
        return ret

    async def execute_client(self, statement, *args, **kwargs):
        """Executes statement; tries special, then client-side."""
        await self.__assure_initialized_cmd()
        statementdata = sl.parse_statement(statement, *args, **kwargs)
        ret, flag = await self.__execute_client_special(statementdata)
        if not flag:
            ret = await self.__execute_client(statementdata)
        return ret

    async def execute_server(self, statement, *args, **kwargs):
        """Executes statement directly on the server."""
        assert isinstance(statement, str)
        await self.__assure_initialized_cmd()
        statementdata = sl.parse_statement(statement, *args, **kwargs)
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
            raise TryAgain(a107.str_exc(e))
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
        if not commandname in self.commands_by_name: raise NotAClientCommand()
        method = self.commands_by_name[commandname].method
        ret = await method(*args, **kwargs)
        return ret

    async def __execute_client_special(self, statementdata):
        commandname, args, kwargs = statementdata
        ret, flag = None, False
        if commandname == "?":
            flag, ret = True, self.__clienthelp(*args, **kwargs)
        return ret, flag

    async def __execute_in_loop(self, st):
        """Executes and prints result."""
        from serverlib.server import CommandError
        try:
            ret = await self.execute(st)
        except (CommandError, ServerError) as e:
            # Here we treat specific exceptions raised by the server
            yoda("That work did not.", False)
            my_print_exception(e)
        except Exception as e:
            yoda("That work did not.", False)
            my_print_exception(e)
            # self.logger.exception(f"Error executing statement '{st}'")
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
            raise ServerError(f"Error from server: {a107.fancilyquoted(a107.str_exc(ret))}")
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

    def __clienthelp(self, what=None, *args, **kwargs):
            if not what:
                name_method = [(k, v.method) for k, v in self.commands_by_name.items() if not "__" in k]
                name_descr = [("?", "print this (client-side help)"),
                              ("help", "server-side help"),
                              ("exit", "exit client"),]
                name_descr.extend([(name, a107.get_obj_doc0(method)) for name, method in name_method])
                headline = "Client-side commands"
                lines = [headline, "="*len(headline), ""]+sl.format_name_method(name_method)
                return "\n".join(lines)
            else:
                if what not in self.commands_by_name:
                    raise ValueError("Invalid method: '{}'. Use '?' to list client-side methods.".format(what))
                return sl.format_method(self.commands_by_name[what].method)

    def __print_result(self, ret):
        yoda("Happy I am.", True)
        print_result(ret)

def yoda(s, happy=True):
    print(attr("bold")+(COLOR_HAPPY if happy else COLOR_SAD), end="")
    print("{0}|o_o|{0} -- {1}".format("^" if happy else "v", s), end="")
    print(attr("reset")*2)


def my_print_exception(e):
    print("{}{}({}){}{} {}{}".format(COLOR_ERROR, attr("bold"), e.__class__.__name__,
                                     attr("reset"), COLOR_ERROR, str(e), attr("reset")))


class NotAClientCommand(Exception):
    pass


class ServerError(Exception): pass


class TryAgain(Exception):
    """Attempt to unify my network error reporting to users of this library (inspired in zmq.Again)."""
    pass


def _powertabulate(rows, header, *args, **kwargs):
    is_whenthis = [h in ("whenthis", "ts", "timestamp", "ts0", "ts1") for h in header]
    is_period = [h == "period" for h in header]
    numcols = len(header)
    if any(is_whenthis) or any(is_period):
        for row in rows:
            for i in range(numcols):
                if is_whenthis[i]: row[i] = a107.dt2str(a107.to_datetime(row[i]))
                elif is_period[i]: row[i] = pl3.QP.to_str(row[i])
    return tabulate.tabulate(rows, header, *args, floatfmt="f", **kwargs)


def _detect_girafales(s):
    lines = s.split("\n")
    return any(line.startswith("-") and line.count("-") > len(line)/2 for line in lines)


def print_result(ret):
    def print_header(k, level):
        print(attr('bold')+COLOR_HEADER+"\n".join(a107.format_h(level+1, k))+attr("reset"))

    def handle_list(arg):
        if len(arg) > 0:
            if isinstance(arg[0], dict):
                excluded = ("info",)
                header = [k for k in arg[0].keys() if k not in excluded]
                rows = [[v for k, v in row.items() if k not in excluded] for row in arg]
                a107.print_girafales(_powertabulate(rows, header))
            else: print("\n".join([str(x) for x in arg]))  # Experimental: join list elements with "\n"
        else: handle_default(arg)

    def handle_dict(arg, level=0):
        if len(arg) > 0:
            first = next(iter(arg.values()))
            if isinstance(first, dict):
                # dict of dicts: converts key to column
                rows = [[k, *v.values()] for k, v in arg.items()]; header = ["key", *first.keys()]
                a107.print_girafales(_powertabulate(rows, header))
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
            else: handle_default(arg)
        else: handle_default(arg)

    def handle_default(arg):
        if not isinstance(arg, str): arg = str(arg)
        if "\n" in arg:
            if _detect_girafales(arg): a107.print_girafales(arg)
            else: print(arg)
        else:
            arg = re.sub(r'\s+', ' ', arg)
            print("\n".join(textwrap.wrap(arg, 80)))

    if isinstance(ret, str): print(ret)
    elif isinstance(ret, tuple) and len(ret) == 2 and isinstance(ret[0], list) and isinstance(ret[1], list):
        # Tries to detect "tabulate-like" (rows, headers) arguments
        a107.print_girafales(_powertabulate((tabulate.tabulate(*ret))))
    elif isinstance(ret, list): handle_list(ret)
    elif isinstance(ret, dict): handle_dict(ret)
    else: handle_default(ret)
