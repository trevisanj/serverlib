class StatementError(Exception):
    pass


class NotAConsoleCommand(Exception):
    pass


class Retry(Exception):
    """Attempt to unify my network error reporting to users of this library (inspired in zmq.Again)."""

    def __init__(self, *args, waittime=None, **kwargs):
        import serverlib as sl
        super().__init__(*args, **kwargs)
        # Use to hint how much time should pass before retrying
        self.waittime = waittime if waittime is not None else sl.lowstate.retry_waittime


class MismatchError(Exception):
    pass
