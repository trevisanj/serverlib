"""
This file starts with "_" to distinguish from serverlib.basicapi.

This is actually a miscellanea file.
"""

__all__ = ["get_metacommands", "get_commands", "get_new_logger"]


from .metacommand import MetaCommand
import inspect, logging, a107, os
from colored import fg, attr
from ..config import config


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
