"""
This file starts with "_" to distinguish from serverlib.basicapi.

This is actually a miscellanea file.
"""

__all__ = ["get_metacommands", "get_commands", "get_new_logger", "ConsoleShelf"]


import inspect, logging, a107, os, serverlib as sl, shelve, time, functools
from .metacommand import MetaCommand
from colored import fg, attr
from .. import errors


RESET = attr("reset")


def get_metacommands(obj, flag_protected=True):
    """Creates list of MetaCommand's based on own methods, which are filtered according to get_methods() rules."""
    return [MetaCommand(method) for method in get_commands(obj, flag_protected)]


# todo this shouldn't be here and should be called get_commands() and is part of sth else, not intelligence
def get_commands(obj, flag_protected=False):
    """Return list of methods that are commands (@servelib.is_command decorator)."""

    ret = [x[1] for x in inspect.getmembers(obj, predicate=inspect.ismethod)
           if (flag_protected or not x[0].startswith("_"))
           and hasattr(x[1], "is_command") and x[1].is_command]
    # for method in ret:
    #     assert inspect.iscoroutinefunction(method), f"Method '{method.__name__}' is not awaitable"
    return ret


def get_new_logger(level, flag_log_console, flag_log_file, fn_log, prefix, name):
    """Creates new logger (automatically creates log file directory if needed)."""
    import serverlib as sl

    logger = logging.Logger(name, level=level)

    if flag_log_file:
        ch = logging.FileHandler(fn_log, "a")
        ch.setFormatter(logging.Formatter(sl.config.logging.filefmt))
        logger.addHandler(ch)

    if flag_log_console:
        ch = logging.StreamHandler()
        ch.setFormatter(a107.ColorFormatter(fmt=sl.config.logging.consolefmt, colors=sl.config.logging.colors))
        logger.addHandler(ch)

    # Prefix indicates whether the logging entity will be a server, client or console, and must end with " "
    if prefix:
        if not prefix.endswith(" "):
            prefix += " "
    else:
        prefix = ""

    logger = logging.LoggerAdapter(logger, {"prefix": prefix})

    return logger





def _locked(f):
    """Decorator for all methods that need exclusive access to shelf"""

    @functools.wraps(f)
    def func(self, *args, **kwargs):
        t = time.time()
        while os.path.isfile(self._lockpath):
            if time.time()-t >= sl.config.shelftimeout:
                raise errors.ShelfTimeout("Console shelf access timeout")
            time.sleep(.001)

        try:
            with open(self._lockpath, "w") as lockfile:
                lockfile.write("Delete me in case of dead lock, no big deal")
                # Opens shelf for use
                self._shelf = shelve.open(self._shelfpath)

                # Original method is called here
                return f(self, *args, **kwargs)
        finally:
            if os.path.isfile(self._lockpath):
                os.unlink(self._lockpath)
            if self._shelf is not None:
                self._shelf.close()
                self._shelf = None

    return func

class ConsoleShelf:
    """
    Open-(read/write)-close layer over Python shelve with lock file
    """

    @_locked
    def __getitem__(self, key):
        return self._shelf[key]

    @_locked
    def get(self, key, default):
        return self._shelf.get(key, default)

    @_locked
    def __setitem__(self, key, value):
        self._shelf[key] = value

    def __init__(self, shelfpath):
        self._shelfdir = os.path.split(shelfpath)[0]
        self._lockpath = os.path.join(self._shelfdir, sl.config.shelflockfilename)
        self._shelfpath = shelfpath
        self._shelf = None



