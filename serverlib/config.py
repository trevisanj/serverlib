__all__ = ["config"]

import logging as lggng

from colored import fg, bg, attr
import tabulate
# from dataclasses import dataclass

# todo improve the explanation below (wtf does "Allows me to create a nicer "Summarize2()" table" mean?)
tabulate.PRESERVE_WHITESPACE = True  # Allows me to create a nicer "Summarize2()" table


RESET = attr("reset")

class config:
    """
    Serverlib configuration

    Values are accessible through the server command "s_getd_all".
    """

    # --- Data Root: diretory to store all serverlib data
    # This will be the same for all applications that use serverlib (a specific subdirectory will be created
    # for each application).
    #
    # Paths will be expanded with os.path.expanduser(), so the "~" character is functional.
    #
    # environment variable to define data root before running application
    datarootenvvar = "SERVERLIB_DATAROOT"
    # default data root
    defaultdataroot = "~/.serverlib"

    # -- Default configuration for serverlib.Waiter instances
    # initial waiting time (seconds)
    waiter_time_start: float = 0.5
    # maximum waiting time (seconds)
    waiter_time_max: int = 30
    # maximum number of attempts
    waiter_maxtries: int = 10

    # -- Other configuration
    # Description width in welcome message
    descriptionwidth = 100

    # -- Exclusive access console shelf
    # lock timeout
    shelftimeout = .2
    # shelf lock filename
    shelflockfilename = "shelf.lock"

    class colors:
        okgreen = fg("green")
        fail = fg("red")
        error = fg("light_red")
        from_server = fg("black")+bg("dark_red_2")
        happy = fg("light_green")
        sad = fg("blue")
        input = fg("orange_1")+attr("bold")
        header = fg("white")
        neutral = fg("cyan")

    class logging:
        # key: whatami
        prefixes = {"server": "S",
                    "client": "C",
                    "console": "O"}
        colors = {
            lggng.DEBUG: fg("light_gray"),
            lggng.INFO: fg("cyan"),
            lggng.WARNING: fg("orange_red_1"),
            lggng.ERROR: fg("light_red")+attr("bold"),
            lggng.CRITICAL: fg("light_red"),
        }

        # Don't remove #color and #reset
        consolefmt = f'#color[%(prefix)s%(name)s %(levelname)s]#reset %(message)s'
        filefmt = '[%(prefix)s%(name)s %(levelname)s] %(message)s'
