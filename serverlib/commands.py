"""Commands, ServerCommands, ClientCommands, ConsoleCommands

These classes did something historically, but now they exist only for grouping purposes. It is nice to see how the
"intelligence" concept took over."""

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


