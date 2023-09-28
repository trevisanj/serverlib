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

    # if not issubclass(cls, sl.ServerCfg):
    #     raise TypeError(f"Class `{cls.__name__}` must descend from `serverlib.ServerCfg`")

    if not hasattr(cls, "_appname") or not cls._appname:
        cls._appname = cls.__name__
    return cls


def is_subapp(appcfgcls):
    """Used to decorate subapp config class

    Makes -- without overwriting -- attributes _appname, _subappname, loggingleve, flag_log_file, flag_log_console
    """

    def copy_attrs(subappcfgcls):
        if not issubclass(subappcfgcls, sl.ServerCfg):
            raise TypeError(f"Class `{subappcfgcls.__name__}` must descend from `serverlib.ServerCfg`")

        subappcfgcls._appname = appcfgcls._appname

        if not subappcfgcls._subappname:
            subappcfgcls._subappname = subappcfgcls.__name__

        for name in ["logginglevel", "flag_log_file", "flag_log_console"]:
            if hasattr(appcfgcls, name) and (not hasattr(subappcfgcls, name) or not getattr(subappcfgcls, name)):
                setattr(subappcfgcls, name, getattr(appcfgcls, name))

        return subappcfgcls

    return copy_attrs


def is_client(servercfgcls):
    """Decorator a cfg class which has client relation to servercls

    Makes -- without overwriting -- attributes _appname, _subappname, loggingleve, flag_log_file, flag_log_console

    """

    def copy_attrs(clientcfgcls):
        if not issubclass(clientcfgcls, sl.ClientCfg):
            raise TypeError(f"Class `{clientcfgcls.__name__}` must descend from `serverlib.ClientCfg`")

        clientcfgcls.port = servercfgcls.port
        clientcfgcls._appname = servercfgcls._appname

        if hasattr(servercfgcls, "_subappname"):
            clientcfgcls._subappname = servercfgcls._subappname

        for name in ["logginglevel", "flag_log_file", "flag_log_console"]:
            if hasattr(servercfgcls, name) and (not hasattr(clientcfgcls, name) or not getattr(clientcfgcls, name)):
                setattr(clientcfgcls, name, getattr(servercfgcls, name))

        return clientcfgcls

    return copy_attrs

