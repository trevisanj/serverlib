"""Commands, ServerCommands, ClientCommands, ConsoleCommands

These classes did something historically, but now they exist only for grouping purposes. It is nice to see how the
"intelligence" concept took over."""

__all__ = ["Commands", "ServerCommands", "ClientCommands", "ConsoleCommands"]

import serverlib as sl, inspect

class Commands(sl.Intelligence):
    """Base class for ServerCommands and ClientCommands."""


class ServerCommands(Commands):
    async def getd_servercfg(self):
        # if not hasattr(self, "cfg"):
        #     return sl.Status("I don't have a .cfg")
        return self.cfg.to_dict()


class ClientCommands(Commands):
    pass


class ConsoleCommands(Commands):
    pass


