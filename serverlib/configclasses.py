"""BaseConfig class"""

__all__ = ["BaseConfig", "ServerConfig", "ClientConfig", "ConsoleConfig"]

import os, a107, configobj, serverlib as sl, random
from .consts import KEBABWIDTH

class BaseConfig:
    """Common functionality for ClientConfig and ServerConfig.

    Implements certain conventions on directories, configuration and log filenames based on the application name, see
    properties.

    Args:
        appname: "umbrella" name affecting self.autodir=="~/.<appname>"
        datadir: data directory. If undefined, falls back to self.autodir
        subappname: "sub-appname". If undefined, falls back to appname. Affects all properties "<*>path".
                Use for complex-structured applications with several servers. Otherwise, use appname and
                leave this.
    """

    defaultsuffix = None
    default_flag_log_file = None

    @property
    def autodir(self):
        """Automatic directory made from self.appname."""
        return os.path.expanduser(f"~/.{self.appname}")

    @property
    def subappname(self):
        """Defaults to self.appname."""
        return self.__subappname if self.__subappname is not None else self.appname

    @subappname.setter
    def subappname(self, value):
        self.__subappname = value

    @property
    def suffix(self):
        """Suffix for filenames. Defaults to self.defaultsubappname."""
        return self.__suffix if self.__suffix is not None else self.defaultsuffix

    @suffix.setter
    def suffix(self, value):
        self.__suffix = value

    @property
    def configdir(self):
        return self.__configdir if self.__configdir is not None else self.autodir

    @property
    def datadir(self):
        return self.__datadir if self.__datadir is not None else self.autodir

    @property
    def reportdir(self):
        return self.__reportdir if self.__reportdir is not None else "/tmp"

    @property
    def configpath(self):
        location = self.configdir
        filename = f"{self.subappname}-{self.suffix}.cfg"
        configpath = os.path.join(location, "cfg", filename)
        return configpath

    @property
    def logpath(self):
        """Returns the path to the '.log' file."""
        return os.path.join(self.datadir, "log", f"{self.subappname}-{self.suffix}.log")

    @property
    def stoppath(self):
        return os.path.join(self.datadir, f"stop-{self.subappname}")

    @property
    def logger(self):
        if self.__logger is None:
            self.__logger = a107.get_new_logger(fn_log=self.logpath,
                                           flag_log_file=self.flag_log_file, flag_log_console=self.flag_log_console,
                                           level=self.logginglevel)
        return self.__logger

    def __init__(self,
                 appname,
                 configdir=None,
                 flag_log_file=None,
                 flag_log_console=None,
                 datadir=None,
                 logginglevel=None,
                 subappname=None,
                 suffix=None,
                 description=None,
                 reportdir=None):
        assert self.defaultsuffix is not None, f"Forgot to set {self.__class__.__name__}.defaultsuffix"
        assert self.default_flag_log_file is not None, f"Forgot to set {self.__class__.__name__}.default_flag_log_file"
        if logginglevel is None: logginglevel = a107.logging_level
        if flag_log_console is None: flag_log_console = a107.flag_log_console
        if flag_log_file is None: flag_log_file = a107.flag_log_file
        self.__configdir = configdir
        self.__datadir = datadir
        self.__reportdir = reportdir
        self.__logger = None
        self.master = None  # Server or Client
        self.appname = appname
        self.flag_log_console = flag_log_console
        self.flag_log_file = flag_log_file if flag_log_file is not None else self.default_flag_log_file
        self.logginglevel = logginglevel
        self.description = description
        self.__subappname = subappname
        self.__suffix = suffix

    def __str__(self):
        return sl.cfg2str(self)

    def to_dict(self):
        return sl.cfg2dict(self)

    def read_configfile(self):
        """This method populates self with attributes found within config file.

        Like this one can override hard-coded attributes.
        """
        configpath = self.configpath
        d, f = os.path.split(configpath)
        if not os.path.isdir(d):
            a107.ensure_path(d)
            self.master.logger.info(f"Created directory '{d}'")
        h = self.__get_configobj()
        for attrname, value in h.items():
            setattr(self, attrname, value)

    def get(self, attrname, default=None):
        """Retrieves attribute with default option."""
        return getattr(self, attrname) if hasattr(self, attrname) else default

    def set(self, attrname, value):
        """Sets value both as self's attribute and within the config file."""
        setattr(self, attrname, value)
        h = self.__get_configobj()
        h[attrname] = value
        h.write()

    def filepath(self, suffix):
        """Builds path to file <datadir>/<subappname><suffix>.

        Example of suffix: "-vars.pickle"
        """
        return os.path.join(self.datadir, f"{self.subappname}{suffix}")

    def get_welcome(self):
        slugtitle = f"Welcome to the '{self.subappname}' {self.suffix}"
        ret = "\n".join(a107.format_slug(slugtitle, random.randint(0, 2)))
        if self.description:
            ret += "\n"+a107.kebab(self.description, KEBABWIDTH)
        return ret

    def __get_configobj(self):
        return configobj.ConfigObj(self.configpath, create_empty=True, unrepr=True)


class ClientServerConfig(BaseConfig):
    """Base class for ClientConfig and ServerConfig."""

    defaulthost = None

    @property
    def url(self):
        return sl.hopo2url((self.host, self.port), self.defaulthost)

    def __init__(self, *args, host=None, port=None, **kwargs):
        assert self.defaulthost is not None, f"Forgot to set {self.__class__.__name__}.defaulthost"
        super().__init__(*args, **kwargs)
        self.host = host
        self.port = port


class ServerConfig(ClientServerConfig):
    """Configuration for servers

    Args:
        sleepinterval: (seconds) time to sleep if didn't receive any requests in serverloop cycle
    """

    defaultsuffix = "server"
    defaulthost = "*"
    default_flag_log_file = True

    def __init__(self, *args, sleepinterval=0.001, **kwargs):
        super().__init__(*args, **kwargs)
        self.sleepinterval = sleepinterval


class _WithHistory:
    """This is a partial class for ClientConfig and ConsoleConfig."""

    @property
    def historypath(self):
        """Returns the path to the history file."""
        return os.path.join(self.datadir, "history", f"{self.subappname}-{self.suffix}.history")


class ClientConfig(ClientServerConfig, _WithHistory):
    """Configuration for clients.

    Introduces the concept of "own identity", as a client may assume the subappname and description of
    the server, or use own subappname and description.
    """

    defaultsuffix = "client"
    defaulthost = "127.0.0.1"
    default_flag_log_file = False

    def __init__(self, *args, flag_ownidentity=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.flag_ownidentity = flag_ownidentity


class ConsoleConfig(BaseConfig, _WithHistory):
    defaultsuffix = "console"
    default_flag_log_file = False
