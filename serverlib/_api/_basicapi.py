"""
This file starts with "_" to distinguish from serverlib.basicapi
"""

__all__ = ["get_metacommands", "get_commands"]


from .metacommand import MetaCommand
import inspect


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
