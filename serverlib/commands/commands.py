"""
Commands classes

    - commands classes are dummy, but they are useful for grouping purposes.

    - (20230710) server commands should all start with "s_" ("s" as in server): becomes clear that server is being
      summoned


"""

__all__ = ["Commands", "ServerCommands", "ClientCommands", "ConsoleCommands"]

import serverlib as sl

class Commands(sl.Intelligence):
    """Base class for ServerCommands and ClientCommands."""


class ServerCommands(Commands):
    pass


class ClientCommands(Commands):
    pass


class ConsoleCommands(Commands):
    pass


