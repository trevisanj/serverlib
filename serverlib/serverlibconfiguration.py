from colored import fg, bg, attr
import tabulate
from dataclasses import dataclass

tabulate.PRESERVE_WHITESPACE = True  # Allows me to create a nicer "Summarize2()" table


COLOR_OKGREEN = fg("green")
COLOR_FAIL = fg("red")
COLOR_ERROR = fg("light_red")
COLOR_FROM_SERVER = fg("black")+bg("dark_red_2")
COLOR_HAPPY = fg("light_green")
COLOR_SAD = fg("blue")
COLOR_INPUT = fg("orange_1")
COLOR_HEADER = fg("white")

RESET = attr("reset")

KEBABWIDTH = 100


@dataclass
class _LowState:
    """
    For the sake of organization, all global configuration and internal state of serverlib are grouped in this class

    One instance of this class -- named "lowstate" -- is created when serverlib is imported. The variables in the
    "configuration" section may be changed.

    Values are accessible through the server command "s_getd_lowstate".
    """

    # CONFIGURATION
    # -------------

    # client timeout in miliseconds
    timeout = 30000

    # Whether to server-side log traceback when command raises exception (to help with debugging)
    flag_log_traceback: bool = True

    # Time to wait before retrying. This value is "informed" by a raised Retry exception
    retry_waittime: float = 1.

    # -- Default configuration for serverlib.Waiter instances
    waiter_time_start: float = 0.5  # initial waiting time
    waiter_time_max: int = 30  # maximum waiting time
    waiter_maxtries: int = 10  # maximum number of attempts


    # INTERNAL VARIABLES (do not change)
    # ------------------
    numsockets: int = 0
    numcontexts: int = 0

lowstate = _LowState()


del fg, bg, attr, tabulate, dataclass

