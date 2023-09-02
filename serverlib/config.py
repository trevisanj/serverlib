import logging as lggng

from colored import fg, bg, attr
import tabulate
# from dataclasses import dataclass

tabulate.PRESERVE_WHITESPACE = True  # Allows me to create a nicer "Summarize2()" table

RESET = attr("reset")


class config:
    """
    Serverlib configuration

    Values are accessible through the server command "s_getd_all".
    """

    class colors:
        okgreen = fg("green")
        fail = fg("red")
        error = fg("light_red")
        from_server = fg("black")+bg("dark_red_2")
        happy = fg("light_green")
        sad = fg("blue")
        input = fg("orange_1")
        header = fg("white")
        neutral = fg("cyan")

    class logging:
        # consolefmt = f'{fg("cyan")}[%(name)s][%(levelname)]{RESET} %(message)s'
        # sc: server-or-client prefix
        consolefmt = f'{fg("cyan")}[%(prefix)s%(name)s %(levelname)s]{RESET} %(message)s'
        filefmt = '[%(prefix)s%(name)s %(levelname)s] %(message)s'
        level = lggng.INFO
        flag_console = False

    class colors:
        okgreen = fg("green")
        fail = fg("red")
        error = fg("light_red")
        from_server = fg("black")+bg("dark_red_2")
        happy = fg("light_green")
        sad = fg("blue")
        input = fg("orange_1")
        header = fg("white")

    # Description width in welcome message
    descriptionwidth = 100

    # client timeout (seconds)
    clienttimeout = 30

    # Whether to server-side log traceback when command raises exception (to help with debugging)
    flag_log_traceback: bool = True

    # Time to wait before retrying. This value is "informed" by a raised Retry exception
    retry_waittime: float = 1.

    # -- Default configuration for serverlib.Waiter instances
    # initial waiting time (seconds)
    waiter_time_start: float = 0.5
    # maximum waiting time (seconds)
    waiter_time_max: int = 30
    # maximum number of attempts
    waiter_maxtries: int = 10


del fg, bg, attr, tabulate

