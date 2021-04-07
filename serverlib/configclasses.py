"""BaseConfig class"""
import os, a107, configobj, logging
from . import whatever

class BaseConfig:
    """Common functionality for ClientConfig and ServerConfig.

    Implements certain conventions on directories, configuration and log filenames based on the application name, see
    properties.
    """
    defaulthost = None
    defaultsuffix = None
    default_flag_log_file = None

    @property
    def autodir(self):
        """Automatic directory made from self.applicationname."""
        return os.path.expanduser(f"~/.{self.applicationname}")

    @property
    def prefix(self):
        """Suffix for filenames. Defaults to self.applicationname."""
        return self.__prefix if self.__prefix is not None else self.applicationname

    @prefix.setter
    def prefix(self, value):
        self.__prefix = value

    @property
    def suffix(self):
        """Suffix for filenames. Defaults to self.defaultprefix."""
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
    def configpath(self):
        location = self.configdir
        filename = f"{self.prefix}-{self.defaultsuffix}.cfg"
        configpath = os.path.join(location, filename)
        return configpath

    @property
    def logpath(self):
        """Returns the path to the '.log' file."""
        return os.path.join(self.datadir, f"{self.prefix}-{self.defaultsuffix}.log")

    @property
    def url(self):
        return whatever.hopo2url((self.host, self.port), self.defaulthost)

    @property
    def stoppath(self):
        return os.path.join(self.datadir, f"stop-{self.prefix}")

    @property
    def logger(self):
        if self.__logger is None:
            self.__logger = a107.get_new_logger(fn_log=self.logpath,
                                           flag_log_file=self.flag_log_file, flag_log_console=self.flag_log_console,
                                           level=self.logginglevel)
        return self.__logger

    def __init__(self, applicationname=None, configdir=None, flag_log_file=None, flag_log_console=False, datadir=None,
                 host=None, port=None, logginglevel=logging.INFO, prefix=None, suffix=None):
        assert self.defaultsuffix is not None, f"Forgot to set {self.__class__.__name__}.suffix"
        assert self.defaulthost is not None, f"Forgot to set {self.__class__.__name__}.defaulthost"
        assert self.default_flag_log_file is not None, f"Forgot to set {self.__class__.__name__}.default_flag_log_file"
        self.__configdir = configdir
        self.__datadir = datadir
        self.__logger = None
        self.master = None  # Server or Client
        self.applicationname = applicationname
        self.flag_log_console = flag_log_console
        self.flag_log_file = flag_log_file if flag_log_file is not None else self.default_flag_log_file
        self.host = host
        self.port = port
        self.logginglevel = logginglevel
        self.__prefix = prefix
        self.__suffix = suffix

    def __str__(self):
        return whatever.cfg2str(self)

    def to_dict(self):
        return whatever.cfg2dict(self)

    def read_configfile(self):
        """This method populates self with attributes found within config file.

        Like this one can override hard-coded attributes.

        If more complex structures are needed, one may consider using other types of storage within the config dir
        """
        configpath = self.configpath
        d, f = os.path.split(configpath)
        if not os.path.isdir(d):
            a107.ensurepath(d)
            self.master.logger.info(f"Created directory '{d}'")
        h = configobj.ConfigObj(configpath, create_empty=True, unrepr=True)
        for attrname, value in h.items():
            setattr(self, attrname, value)


class ServerConfig(BaseConfig):
    """Configuration for servers

    Args:
        sleepinterval: (seconds) time to sleep after each interation of main loop
    """

    defaultsuffix = "server"
    defaulthost = "*"
    default_flag_log_file = True

    def __init__(self, *args, sleepinterval=0.1, servername=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sleepinterval = sleepinterval
        self.__servername = servername


class ClientConfig(BaseConfig):
    """Configuration for clients."""

    defaultsuffix = "client"
    defaulthost = "127.0.0.1"
    default_flag_log_file = False

    @property
    def historypath(self):
        """Returns the path to the history file."""
        return os.path.join(self.datadir, f"{self.prefix}-{self.defaultsuffix}.history")
