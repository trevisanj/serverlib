"""
Some features are shared between Console and Client
"""

__all__ = ["StatementData", "parse_statement", "yoda", "my_print_exception"]

import a107
from dataclasses import dataclass
from typing import List
from colored import fg, bg, attr
from serverlib.serverlibconfiguration import *
from enum import IntEnum


class CST(IntEnum):
    """Console/Client states"""

    INIT = 0  # still in __init__()
    ALIVE = 10  # passed __init__()
    INITIALIZED = 20  # inited commands
    LOOP = 30  # looping in command-line interface
    STOPPED = 40  # stopped
    CLOSED = 50


@dataclass
class StatementData:
    commandname: str
    args: List
    kwargs: List
    outputfilename: str
    flag_server: bool


def parse_statement(statement, args_, kwargs_):
    """Parses statement and returns StatementData"""
    statement = statement.lstrip()
    outputfilename = None
    flag_server = False
    try:
        index = statement.index(" ")
    except ValueError:
        commandname, args, kwargs = statement, [], {}
    else:
        commandname = statement[:index]
        args, kwargs = a107.str2args(statement[index+1:])
    if commandname.startswith(">"):
        commandname = commandname[1:]
        flag_server = True
    elif commandname == "?":
        commandname = "help"
    if args_: args.extend(args_)
    if kwargs_: kwargs.update(kwargs_)
    if args:
        if isinstance(args[-1], str) and args[-1].startswith(">>>"):
            outputfilename = args.pop()[3:]
    ret = StatementData(commandname, args, kwargs, outputfilename, flag_server)
    return ret



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

