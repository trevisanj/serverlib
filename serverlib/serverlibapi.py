"""This is the serverlib internal API."""
import re, textwrap, a107, inspect
from colored import fg, attr, bg


__all__ = ["hopo2url", "myprint", "get_methods", "get_commandnames", "format_name_method", "format_description",
           "format_method", "cfg2str", "cfg2dict", "WithCommands", "Commands", "ClientCommands", "Command", 
           "ServerCommands", "parse_statement",]


class Command:
    def __init__(self, method):
        self.method = method
        self.name = method.__name__
        pars = inspect.signature(method).parameters
        # Note: flag_bargs is only effective on the server side
        flag_bargs = "bargs" in pars
        if flag_bargs and len(pars) > 1:
            raise AssertionError(f"Method {self.name} has argument named 'bargs' which identifies it as a bytes-accepting method, but has extra arguments")
        self.flag_bargs = flag_bargs


class Commands(object):
    _name = None

    @property
    def cfg(self):
        return self.master.cfg

    @property
    def logger(self):
        return self.master.cfg.logger

    @staticmethod
    def to_list(args):
        """Converts bytes to list of strings."""
        return [x for x in args.decode().split(" ") if len(x) > 0]

    @property
    def name(self):
        if self._name: return self._name
        return self.__class__.__name__

    def __init__(self):
        self.master = None


class ClientCommands(Commands):
    """
    Client-side "commands" which translate to client.execute(...) (i.e., calls to the server)
    """

    def __init__(self):
        super().__init__()
        self.master = None


class ServerCommands(Commands):
    """
    Class that implements all server-side "commands".

    Notes:
        - Subclass this to implement new commands
        - All arguments come as bytes
        - Don't forget to make them all "async"
    """


class WithCommands:
    """Server/Client ancestor."""

    def __init__(self):
        # list of ServerCommands objects
        self.cmdcmd = []
        # {cmd.name: cmd, ...}
        self.cmd_by_name = {}
        # {commandname: Command, ...}, synthesized from all self.cmdcmd
        self.commands_by_name = {}

    def attach_cmd(self, cmdcmd):
        """Attaches one or more ServerCommands instances.

        This method is not async because it was designed to be called from __init__().
        """
        if not isinstance(cmdcmd, (list, tuple)): cmdcmd = [cmdcmd]
        for cmd in cmdcmd:
            if not isinstance(cmd, Commands): raise TypeError(f"Invalid commands type: {cmd.__class__.__name__}")
        for cmd in cmdcmd:
            cmd.master = self
            self.cmdcmd.append(cmd)
            self.cmd_by_name[cmd.name] = cmd
            for name, method in get_methods(cmd, flag_protected=True):
                self.commands_by_name[name] = Command(method)


def format_name_method(name_method):
    """Formats name and method for help printing. Returns in the form of list."""
    if len(name_method) == 0:
        return []
    maxlen = max([len(x[0]) for x in name_method])
    return ["{}{:>{}}{} -- {}".format(attr("bold"), name, maxlen, attr("reset"), a107.get_obj_doc0(method))
            for name, method in name_method]


def format_description(description):
    """Formats name and method for help printing. Returns in the form of list."""
    return [f"{fg('light_yellow')}{description}{attr('reset')}"]


def format_method(method):
    """Formats method for help printing."""
    sig = str(inspect.signature(method)).replace("(", "").replace(")", "").replace(",", "")
    return "{}{} {}{}\n\n{}".format(attr("bold"), method.__name__, sig, attr("reset"), method.__doc__)


def get_commandnames(obj):
    """Return the names of the "commands" in obj."""
    return [x[0] for x in get_methods(obj)]


def get_methods(obj, flag_protected=False):
    """Return [(name, method), ...] for the "commands" in obj."""
    return [x for x in inspect.getmembers(obj, predicate=inspect.ismethod) if not x[0].startswith("__") and (flag_protected or not x[0].startswith("_"))]


def hopo2url(hopo, fallbackhost="127.0.0.1"):
    """Resolves (host, port) tuple into URL string."""
    if isinstance(hopo, int):
        # Only port was specified
        host = fallbackhost
        port = hopo
    elif isinstance(hopo, str):
        host = hopo
        port = None
    else:
        host = hopo[0]
        port = int(hopo[1])
    if host is None:
        host = fallbackhost
    h = f"tcp://{host}" if "/" not in host else host
    return h if port is None else f"{h}:{port}"


def myprint(x):
    """
    Used to print results from client statements supposedly in a comprehensive manner.

    Note: I tried this in many ways; simply using textwrap seems to be way better than
    a107.make_code_readable(), pprint, pprintpp or autopep8.
    """

    if not isinstance(x, str):
        x = repr(x)
    x = x.replace("\n", "")
    x = re.sub(r'\s+', ' ', x)
    print("\n".join(textwrap.wrap(x, 80)))


def cfg2str(cfg, flag_clean=True):
    """Converts AnguishConfig object into string.

    Args:
        cfg:
        flag_clean: if True, skips attributes that do not render nicely, such as "<object object at 0x7f93a4aa6160>"
    """
    l = []
    for attrname in dir(cfg):
        if not attrname.startswith("_"):
            attr = getattr(cfg, attrname)
            s = repr(attr)
            if flag_clean and "object at" in s:
                continue
            if len(s) > 150:
                s = s[:75]+" ... "+s[-75:]

            l.append(f"{attrname}={s}")
    return "\n".join(l)


def cfg2dict(cfg, flag_clean=True):
    """Converts AnguishConfig object into string.

        Args:
            cfg:
            flag_clean: if True, skips attributes that do not render nicely, such as "<object object at 0x7f93a4aa6160>"
        """
    ret = {}
    for attrname in dir(cfg):
        if not attrname.startswith("_"):
            attr = getattr(cfg, attrname)
            s = repr(attr)
            if flag_clean and s[0] == "<":
                continue
            ret[attrname] = attr

    return ret


def parse_statement(statement, *args_, **kwargs_):
    """Parses statement and returns (commandname, args, kwargs)"""
    try:
        index = statement.index(" ")
    except ValueError:
        commandname, args, kwargs = statement, [], {}
    else:
        commandname = statement[:index]
        args, kwargs = a107.str2args(statement[index+1:])
    if args_: args.extend(args_)
    if kwargs_: kwargs.update(kwargs_)
    return commandname, args, kwargs