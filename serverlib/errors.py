class StatementError(Exception):
    pass


class NotAConsoleCommand(Exception):
    pass


class Retry(Exception):
    """
    Thrown in case of failed operation, but there is hope is retried.

    This exception may optionally carry a suggested time to wait before retrying. For instance, the agent server
    catches this and used this time if available.

    This class was inspired by zmq.Again.
    """

    def __init__(self, *args, waittime=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.waittime = waittime


class MismatchError(Exception):
    pass


class ShelfTimeout(Exception):
    """Timeout waiting for console shelf lock file """
    pass
