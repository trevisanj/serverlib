"""MetaCommand and MetaCommands classes. They are useful both for utilization and stylization."""

__all__ = ["MetaCommand"]

import inspect, a107

class MetaCommand:
    @property
    def oneliner(self):
        return a107.get_obj_doc0(self.method)

    def __init__(self, method):
        self.method = method
        self.name = method.__name__
        pars = inspect.signature(method).parameters
        # Note: flag_bargs is only effective on the server side
        flag_bargs = "bargs" in pars
        if flag_bargs and len(pars) > 1:
            raise AssertionError(f"Method {self.name} has argument named 'bargs' which identifies it as a bytes-accepting method, but has extra arguments")
        self.flag_bargs = flag_bargs
