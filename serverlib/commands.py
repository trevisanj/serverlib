import inspect
import a107
import pickle
__all__ = ["ClientCommands", "_Commands"]

class _Commands(object):
    @property
    def cfg(self):
        return self.master.cfg

    def __init__(self):
        self.master = None

class ClientCommands(_Commands):
    """
    Client-side "commands" which translate to client.execute(...) (i.e., calls to the server)
    """

    def __init__(self):
        super().__init__()
        self.client = None
