import atexit, sys, signal, readline, zmq, zmq.asyncio, pickle, tabulate, a107, traceback, time
from colored import fg, attr
from . import whatever

import csv

__all__ = ["Client"]

TIMEOUT = 30000  # miliseconds to wait until server replies
COLOR_OKGREEN = fg("green")
COLOR_FAIL = fg("red")
COLOR_ERROR = fg("light_red")
COLOR_HAPPY = fg("light_green")
COLOR_SAD = fg("blue")
COLOR_INPUT = fg("orange_1")


class Client(object):
    """
    PannaClient

    Client connects to URL and sends command through execute().
    """

    @property
    def logger(self):
        return self.cfg.logger

    @property
    def cmd(self):
        return self.__cmd

    @cmd.setter
    def cmd(self, value):
        self.__cmd = value
        if value is not None:
            value.client = self

    @property
    def socket(self):
        if self.__ctx is None:
            self.__make_context()
        if self.__socket is None:
            self.__make_socket()
        return self.__socket

    def __init__(self, cfg, cmd=None):
        self.cfg = cfg
        self.__cmd = None
        self.cmd = cmd
        self.__ctx = None
        self.__socket = None
        self.flag_needs_to_reset_colors = False

    def close(self):
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

    async def execute_server(self, st, *args_):
        """
        Sends statement to server, receives reply, unpickles and returns.

        Args:
            st: str in the form "<command> <data>". If *args is passed, statement
                       won't be allowed to have a space (i.e., " ")
            *args_: if passed, will be pickled and concatenated with statement using a " " separator

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
        args = _str2args(sdata)
        # Extends argument list with additional arguments
        if args_:
            args.extend(args_)
        # Mounts binary statement and sends off
        bst = commandname.encode()+b" "+pickle.dumps(args)
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
            # Recreating socket in case of timeout
            # https://stackoverflow.com/questions/41009900/python-zmq-operation-cannot-be-accomplished-in-current-state
            self.__make_socket()
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
            pass

    async def __execute_in_loop(self, st):
        """Executes and prints result."""
        from serverlib.server import CommandError
        try:
            ret = await self.execute(st)
        except CommandError as e:
            # Here we treat specific exceptions raised by the server
            yoda("That work did not.", False)
            my_print_exception(e)
            # self.logger.exception(f"Error executing statement '{st}'")
        except Exception as e:
            yoda("That work did not.", False)
            my_print_exception(e)
            # Cannot log as error, otherwise the traceback always gets printed to the console
            whatever.log_exception(self.logger, e, f"Error executing statement '{st}'\n")
        else:
            self.__print_result(ret)

    def __intercept_exit(self):
        # This one gets called at Ctrl+C, but ...
        def _atexit():
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
        flag_defaultprint = False
        if isinstance(ret, str):
            print(ret)
        # Tries to detect "tabulate-like" (rows, headers) arguments
        elif isinstance(ret, tuple) and len(ret) == 2 and isinstance(ret[0], list) and isinstance(ret[1], list):
            print(tabulate.tabulate(*ret))
        else:
            flag_defaultprint = True
        if flag_defaultprint:
            whatever.myprint(ret)

    def __make_socket(self):
        if self.__socket is not None:
            self.__socket.setsockopt(zmq.LINGER, 0)
            self.__socket.close()
        self.__socket = self.__ctx.socket(zmq.REQ)
        self.__socket.setsockopt(zmq.SNDTIMEO, TIMEOUT)
        self.__socket.setsockopt(zmq.RCVTIMEO, TIMEOUT)
        print(f"Connecting ``{self.cfg.applicationname}'' to {self.cfg.url} ...")
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
        if not commandname in whatever.get_commandnames(self.cmd):
            raise NotAClientCommand()
        if index is not None: sdata = st[index+1:]
        args = _str2args(sdata)
        method = self.cmd.__getattribute__(commandname)
        ret = await method(*args)
        return ret

    def __clienthelp(self, what):
            if not what:
                name_method = whatever.get_methods(self.cmd)
                name_descr = [("?", "print this (client-side help)"),
                              ("help", "server-side help"),
                              ("exit", "exit client"),]
                name_descr.extend([(name, a107.get_obj_doc0(method)) for name, method in name_method])
                headline = "Client-side commands"
                lines = [headline, "="*len(headline), ""]+whatever.format_name_method(name_method)
                return "\n".join(lines)
            else:
                if what not in whatever.get_commandnames(self.cmd):
                    raise ValueError("Invalid method: '{}'. Use '?' to list client-side methods.".format(what))
                return whatever.format_method(getattr(self.cmd, what))

    def __process_result(self, b):
        ret = pickle.loads(b)
        if isinstance(ret, Exception):
            raise ret
        return ret

    def __close(self):
        self.__socket.close()
        self.__ctx.destroy()


def _str2args(sargs):
    """Converts string into a list of arguments using the CSV library."""
    ret = []
    if sargs:
        reader = csv.reader([sargs], delimiter=" ", skipinitialspace=True)
        ret = [[x.strip() for x in row] for row in reader][0]
    return ret


def yoda(s, happy=True):
    print(attr("bold")+(COLOR_HAPPY if happy else COLOR_SAD), end="")
    print("{0}|o_o|{0} -- {1}".format("^" if happy else "v", s), end="")
    print(attr("reset")*2)


def my_print_exception(e):
    print("{}{}({}){}{} {}{}".format(COLOR_ERROR, attr("bold"), e.__class__.__name__,
                                     attr("reset"), COLOR_ERROR, str(e), attr("reset")))


class NotAClientCommand(Exception):
    pass
