__all__ = ["Commands", "ServerCommands", "ClientCommands", "ConsoleCommands"]

import serverlib as sl, inspect

class Commands(sl.Intelligence):
    """Base class for ServerCommands and ClientCommands."""


class ServerCommands(Commands):
    pass


class ClientCommands(Commands):
    pass


class ConsoleCommands(Commands):
    pass


