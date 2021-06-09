"""BaseConfig class"""
import os, a107, configobj, serverlib as sl
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
        """Prefix for filenames. Defaults to self.applicationname."""
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
        configpath = os.path.join(location, "cfg", filename)
        return configpath

    @property
    def logpath(self):
        """Returns the path to the '.log' file."""
        return os.path.join(self.datadir, "log", f"{self.prefix}-{self.defaultsuffix}.log")

    @property
    def url(self):
        return sl.hopo2url((self.host, self.port), self.defaulthost)

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

    def __init__(self, applicationname=None, configdir=None, flag_log_file=None, flag_log_console=None, datadir=None,
                 host=None, port=None, logginglevel=None, prefix=None, suffix=None, description=None):
        assert self.defaultsuffix is not None, f"Forgot to set {self.__class__.__name__}.suffix"
        assert self.defaulthost is not None, f"Forgot to set {self.__class__.__name__}.defaulthost"
        assert self.default_flag_log_file is not None, f"Forgot to set {self.__class__.__name__}.default_flag_log_file"
        if logginglevel is None: logginglevel = a107.logging_level
        if flag_log_console is None: flag_log_console = a107.flag_log_console
        if flag_log_file is None: flag_log_file = a107.flag_log_file
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
        self.description = description
        self.__prefix = prefix
        self.__suffix = suffix

    def __str__(self):
        return sl.cfg2str(self)

    def to_dict(self):
        return sl.cfg2dict(self)

    def read_configfile(self):
        """This method populates self with attributes found within config file.

        Like this one can override hard-coded attributes.

        If more complex structures are needed, one may consider using other types of storage within the config dir
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
        """Builds path to file <datadir>/<prefix><suffix>.

        Example of suffix: "-vars.pickle"
        """
        return os.path.join(self.datadir, f"{self.prefix}{suffix}")

    def __get_configobj(self):
        return configobj.ConfigObj(self.configpath, create_empty=True, unrepr=True)


class ServerConfig(BaseConfig):
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


class ClientConfig(BaseConfig):
    """Configuration for clients."""

    defaultsuffix = "client"
    defaulthost = "127.0.0.1"
    default_flag_log_file = False

    @property
    def historypath(self):
        """Returns the path to the history file."""
        return os.path.join(self.datadir, "history", f"{self.prefix}-{self.defaultsuffix}.history")
