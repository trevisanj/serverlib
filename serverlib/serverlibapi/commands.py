__all__ = ["Commands", "ServerCommands", "ClientCommands"]

import serverlib as sl, inspect

class Commands(sl.Intelligence):
    """Base class for ServerCommands and ClientCommands.

    __init__() takes no arguments (self.master will be assigned later when command is attached to server).
    """
    def __init__(self):
            super().__init__(None)

    def __get_meta__(self, flag_protected=True):
        """Returns list of MetaCommand objects filtered according to rules."""
        return [sl.MetaCommand(method) for method in self.__get_methods__(flag_protected)]

    def __get_methods__(self, flag_protected=False):
        """Return list of methods according to filter rules."""
        return [x[1] for x in inspect.getmembers(self, predicate=inspect.ismethod)
                if "__" not in x[0] and (flag_protected or not x[0].startswith("_"))
                   and x[0] not in ("initialize", "close",)]



class ServerCommands(Commands):
    pass


class ClientCommands(Commands):
    pass
