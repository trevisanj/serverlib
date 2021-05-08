import atexit, sys, signal, readline, zmq, zmq.asyncio, pickle, tabulate, a107, time, serverlib as sl, shlex
from colored import fg, attr

__all__ = ["Client", "ServerError"]

tabulate.PRESERVE_WHITESPACE = True  # Allows me to create a nicer "Summarize2()" table

TIMEOUT = 30000  # miliseconds to wait until server replies
COLOR_OKGREEN = fg("green")
COLOR_FAIL = fg("red")
COLOR_ERROR = fg("light_red")
COLOR_HAPPY = fg("light_green")
COLOR_SAD = fg("blue")
COLOR_INPUT = fg("orange_1")


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
        self.__inited = False
        super().__init__()
        self.__state = sl.ST_INIT
        self.cfg = cfg
        self.flag_needs_to_reset_colors = False
        if cmd is not None: self.attach_cmd(cmd)
        self.__state = sl.ST_ALIVE
        self.__ctx, self.__socket = None, None
        self.__inited = True

    def __del__(self):
        """It is essential to close the zmq stuff, otherwise the async loop event hangs forever."""
        if self.__inited: self.__close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.__close()

    async def connect(self):
        _ = self.socket

    async def close(self):
        self.__close()

    async def execute(self, st):
        """
        Executes statement as if typed in the run console and returns result.

        Args:
            st: (str) statement
        """
        if st == "?" or st[:2] == "? ":
            ret = self.__clienthelp(st[2:])
        else:
            is_clientcommand = True
            try:
                ret = await self.__process_as_clientcommand(st)
            except NotAClientCommand:
                is_clientcommand = False
            if not is_clientcommand:
                ret = await self.execute_server(st)
        return ret

    async def execute_server(self, st, *args_, **kwargs_):
        """
        Sends statement to server, receives reply, unpickles and returns.

        Args:
            st: str in the form "<command> <data>".
            *args_: alternatively, additional arguments.

        Returns:
            ret: either result or exception raised on the server (does not raise)
        """
        assert isinstance(st, str)
        # Splits statement; converts arguments to list
        sdata, index = "", None
        try: index = st.index(" ")
        except ValueError: commandname = st
        else: commandname = st[:index]
        if index is not None: sdata = st[index+1:]
        args, kwargs = _str2args(sdata)
        # Extends argument list with additional arguments
        if args_: args.extend(args_)
        if kwargs_: kwargs.update(kwargs_)
        # Mounts binary statement and sends off
        bst = commandname.encode()+b" "+pickle.dumps([args, kwargs])
        return await self.execute_bytes(bst)

    async def execute_bytes(self, bst):
        """Sents statement to server, receives reply, unpickles and returns.

        Args:
            bst: bytes in the form "<command> <data>".

        Returns:
            ret: either result or exception raised on the server (does not raise)
        """
        try:
            await self.socket.send(bst)
            b = await self.socket.recv()
        except zmq.Again:
            # Will re-create socket in case of timeout
            # https://stackoverflow.com/questions/41009900/python-zmq-operation-cannot-be-accomplished-in-current-state
            self.__del_socket()
            raise

        ret = self.__process_result(b)
        return ret

    async def run(self):
        """Will run client and automatically exit the program.

        Exits because it registers handlers to intercept Ctrl+C and Ctrl+Z.
        """

        self.__intercept_exit()
        self.__set_historylength()
        print(await self.execute_server("_get_welcome"))  # Retrieves and prints welcome message from server
        srvprefix = await self.execute_server("_get_prefix") # Gets server name in order to compose local prompt
        self.__state = sl.ST_LOOP
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
            self.__state = sl.ST_STOPPED

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
            a107.ensure_path()
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

    def __print_result(self, ret):
        yoda("Happy I am.", True)
        flag_defaultprint = True
        if isinstance(ret, str):
            print(ret)
            flag_defaultprint = False
        elif isinstance(ret, tuple) and len(ret) == 2 and isinstance(ret[0], list) and isinstance(ret[1], list):
            # Tries to detect "tabulate-like" (rows, headers) arguments
            print(tabulate.tabulate(*ret))
            flag_defaultprint = False
        elif isinstance(ret, list):
            if len(ret) > 0:
                if isinstance(ret[0], dict):
                    a107.print_girafales(tabulate.tabulate([list(row.values()) for row in ret], list(ret[0].keys())))
                    flag_defaultprint = False
                else:
                    print("\n".join([str(x) for x in ret]))  # Experimental: join list elements with "\n"
                    flag_defaultprint = False
        elif isinstance(ret, dict):
            if len(ret) > 0:
                first = next(iter(ret.values()))
                if isinstance(first, dict):  # dict of dicts: converts key to column
                    rows = [[k, *v.values()] for k, v in ret.items()]; header = ["key", *first.keys()]
                    a107.print_girafales(tabulate.tabulate(rows, header))
                    flag_defaultprint = False
        else:
            flag_defaultprint = True
        if flag_defaultprint:
            sl.myprint(ret)

    def __make_socket(self):
        self.__del_socket()
        self.__socket = self.__ctx.socket(zmq.REQ)
        self.__socket.setsockopt(zmq.SNDTIMEO, TIMEOUT)
        self.__socket.setsockopt(zmq.RCVTIMEO, TIMEOUT)
        print(f"Connecting ``{self.cfg.prefix}(client)'' to {self.cfg.url} ...")
        self.__socket.connect(self.cfg.url)

    def __make_context(self):
        self.__ctx = zmq.asyncio.Context()

    async def __process_as_clientcommand(self, st):
        """In the client, statement is processed as CSV

        Args:
            st: (string)

        Returns:
            ret: whatever the client command returns, or raises NotAClientCommand
        """
        sdata, index = "", None
        try: index = st.index(" ")
        except ValueError: commandname = st
        else: commandname = st[:index]
        if not commandname in self.commands_by_name:
            raise NotAClientCommand()
        if index is not None: sdata = st[index+1:]
        args = _str2args(sdata)
        method = self.commands_by_name[commandname].method
        ret = await method(*args[0], **args[1])
        return ret

    def __clienthelp(self, what):
            if not what:
                name_method = [(k, v.method) for k, v in self.commands_by_name.items() if not k.startswith("_")]
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

    def __process_result(self, b):
        ret = pickle.loads(b)
        if isinstance(ret, Exception):
            raise ServerError(f"Error from server: ``{a107.str_exc(ret)}''")
        return ret

    def __close(self):
        # print(f"{self.__class__.__name__} CLOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
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

def _str2args(sargs):
    """Converts string into a list of arguments using the CSV library. Update: it now parses kwargs as well"""
    args, kwargs = [], {}
    for part in shlex.split(sargs):
        try:
            idx = part.index("=")
            kwargs[part[:idx]] = part[idx+1:]
        except ValueError:
            args.append(part)
    return args, kwargs


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