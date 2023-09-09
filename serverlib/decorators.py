__all__ = ["is_app", "is_subapp", "is_client", "is_loop", "is_command"]

import serverlib as sl


def is_command(method):
    method.is_command = True
    return method


def is_loop(method):
    method.is_loop = True
    return method


def is_app(cls):
    """Used to decorate app config class."""

    if not issubclass(cls, sl.ServerCfg):
        raise TypeError(f"Class `{cls.__name__}` must descend from `serverlib.ServerCfg`")

    if not cls._appname:
        cls.__appname = cls.__name__
    return cls


def is_subapp(cls):
    """Used to decorate subapp config class."""

    if not issubclass(cls, sl.ServerCfg):
        raise TypeError(f"Class `{cls.__name__}` must descend from `serverlib.ServerCfg`")

    if not cls._subappname:
        cls._subappname = cls.__name__

    return cls


def is_client(servercls):
    """Decorator a cfg class which has client relation to servercls"""

    def copy_attrs(cls):
        if not issubclass(cls, sl.ClientCfg):
            raise TypeError(f"Class `{cls.__name__}` must descend from `serverlib.ClientCfg`")

        cls.port = servercls.port
        cls._appname = servercls._appname
        if hasattr(servercls, "_subappname"):
            cls._subappname = servercls._subappname

        return cls

    return copy_attrs

