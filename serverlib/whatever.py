"""This is the serverlib internal API."""
import re, textwrap, a107, inspect, traceback
from colored import fg, attr


__all__ = ["hopo2url", "myprint", "get_methods", "get_commandnames", "format_name_method",
           "format_method", "cfg2str", "cfg2dict", "log_exception"]


def log_exception(logger, e, title):
    """Standard way to log an exception.

    I found out that apparently the console is always polluted if we call logger.exception(), so I am calling
    ...info() instead."""
    logger.info(title+a107.str_exc(e)+"\n"+traceback.format_exc())


def format_name_method(name_method):
    """Formats name and method for help printing."""
    if len(name_method) == 0:
        return []
    maxlen = max([len(x[0]) for x in name_method])
    return ["{}{:>{}}{} -- {}".format(attr("bold"), name, maxlen, attr("reset"), a107.get_obj_doc0(method))
            for name, method in name_method]


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