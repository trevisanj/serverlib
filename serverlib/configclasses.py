"""BaseConfig class"""

__all__ = ["BaseConfig", "ServerConfig", "ClientConfig", "ConsoleConfig"]

import os, a107, configobj, serverlib as sl, random
from . import config, _api

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
        cfg: other BaseConfig. If passed, appname and subappname will be taken from this cfg.
             It has precedence over appname and subappname

    Howto:

        - add configurable attribute: override __init__()
    """


    # Prefix in logging messages to distinguish client from server
    loggingprefix = ""

    # Suffix to show on certain occasions
    defaultsuffix = ""

    default_flag_log_file = False

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
    def configfilename(self):
        filename = f"{self.subappname}{self.dash_suffix_or_not()}.cfg"
        return filename

    @property
    def configpath(self):
        configpath = os.path.join(self.configdir, "cfg", self.configfilename)
        return configpath

    @property
    def logpath(self):
        """Returns the path to the '.log' file."""
        return os.path.join(self.datadir, "log", f"{self.subappname}{self.dash_suffix_or_not()}.log")

    @property
    def stoppath(self):
        return os.path.join(self.datadir, f"stop-{self.subappname}")

    @property
    def logger(self):
        if self.__logger is None:
            flag_created_dir = False
            if self.flag_log_file:
                dir_ = os.path.split(self.logpath)[0]
                if dir_:
                    flag_created_dir = a107.ensure_path(dir_)

            self.__logger = _api.get_new_logger(fn_log=self.logpath,
                                                flag_log_file=self.flag_log_file,
                                                flag_log_console=self.flag_log_console,
                                                level=self.logginglevel,
                                                prefix = self.loggingprefix,
                                                name=self.subappname)

            if flag_created_dir:
                self.logger.info(f"Created directory '{dir_}'")

        return self.__logger

    def __init__(self,
                 appname=None,
                 configdir=None,
                 flag_log_file=None,
                 flag_log_console=None,
                 datadir=None,
                 logginglevel=None,
                 subappname=None,
                 suffix=None,
                 description=None,
                 reportdir=None,
                 defaultsuffix=None,
                 cfg=None,
                 ):
        if defaultsuffix is not None:
            self.defaultsuffix = defaultsuffix
        if logginglevel is None:
            logginglevel = config.logging.level
        if flag_log_console is None:
            flag_log_console = config.logging.flag_console

        assert self.defaultsuffix is not None, f"Forgot to set {self.__class__.__name__}.defaultsuffix"
        assert self.default_flag_log_file is not None, f"Forgot to set {self.__class__.__name__}.default_flag_log_file"

        self.flag_log_file = flag_log_file if flag_log_file is not None else self.default_flag_log_file
        self.flag_log_console = flag_log_console
        self.logginglevel = logginglevel

        if cfg is not None:
            appname = cfg.appname
            subappname = cfg.subappname

        assert appname is not None, "appname has not been assigned either explicitly or with cfg"


        self.master = None  # Server or Client
        self.appname = appname
        self.description = description

        self.__configdir = configdir
        self.__datadir = datadir
        self.__reportdir = reportdir
        self.__logger = None
        self.__subappname = subappname
        self.__suffix = suffix

    def __str__(self):
        return sl.cfg2str(self)

    def dash_suffix_or_not(self, suffix=None):
        """Eventually prefixes suffix with a "-"

        Args:
            suffix: defaults to self.suffix

        Returns:
            "-"+(suffix or self.suffix), or ""

            a) if suffix is empty, returns ""
            b) if suffix starts with ".", does not precede suffix with a "-"
            c) if suffix is not empty and does not start with a (".", "-"), precedes it with a "-"
        """
        if suffix is None:
            suffix = self.suffix
        if not suffix: return ""
        if suffix.startswith((".", "-")):
            return suffix
        return f"-{suffix}"

    def to_dict(self):
        return sl.cfg2dict(self)

    def read_configfile(self):
        """This method populates self with attributes found within config file.

        Like this one can override hard-coded attributes.

        Looks for files:
            1. '<self.configpath>'
            2. './<self.configfilename>'

        Both files will be used if present; settings in (2) may ovewrite settings in (1) above.

        Use case: one way to create a custom "client" directory is to:
            - run ```saccapoke.py```
            - copy ~/.sacca/cfg/*client.cfg to some directory
            - then change whatever you want
        """

        def _populate_self(h):
            for attrname, value in h.items():
                setattr(self, attrname, value)

        configpath = self.configpath
        d, f = os.path.split(configpath)
        if not os.path.isdir(d):
            a107.ensure_path(d)
            self.logger.info(f"Created directory '{d}'")
        h = self.__get_configobj_with_path(configpath, True)
        _populate_self(h)

        localpath = os.path.join(".", self.configfilename)
        if os.path.isfile(localpath):
            h = self.__get_configobj_with_path(localpath, False)
            _populate_self(h)

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
        return os.path.join(self.datadir, f"{self.subappname}{self.dash_suffix_or_not(suffix)}")

    def get_welcome(self):
        slugtitle = f"Welcome to the '{self.subappname}' {self.suffix}"
        ret = "\n".join(a107.format_slug(slugtitle, random.randint(0, 2)))
        if self.description:
            ret += "\n"+a107.kebab(self.description, config.descriptionwidth)
        return ret

    def __get_configobj_with_path(self, path_, flag_create_empty):
        """Gets config for specific file path."""
        flag_exists = os.path.isfile(path_)
        ret = configobj.ConfigObj(path_, create_empty=flag_create_empty, unrepr=True)
        flag_exists_ = os.path.isfile(path_)
        if flag_exists_ != flag_exists:
            self.logger.info(f"Created file '{path_}'")
        return ret

    def __get_configobj(self):
        """Gets config in local path or in configuration directory, whichever is found first."""
        localpath = os.path.join(".", self.configfilename)
        if os.path.isfile(localpath):
            ret = self.__get_configobj_with_path(localpath, False)
        else:
            configpath = self.configpath
            d, f = os.path.split(configpath)
            if not os.path.isdir(d):
                a107.ensure_path(d)
                self.logger.info(f"Created directory '{d}'")
            ret = self.__get_configobj_with_path(configpath, True)
        return ret


class ClientServerConfig(BaseConfig):
    """Base class for ClientConfig and ServerConfig.

    If cfg is passed, port will be taken from cfg (precedence over port argument).
    """

    defaulthost = None

    @property
    def url(self):
        return sl.hopo2url((self.host, self.port), self.defaulthost)

    def __init__(self, *args, host=None, port=None, cfg=None, **kwargs):
        assert self.defaulthost is not None, f"Forgot to set {self.__class__.__name__}.defaulthost"
        super().__init__(*args, cfg=cfg, **kwargs)

        if cfg is not None:
            port = cfg.port

        self.host = host
        self.port = port


class ServerConfig(ClientServerConfig):
    """Configuration for servers

    Args:
        sleepinterval: (seconds) time to sleep if didn't receive any requests in serverloop cycle
    """

    loggingprefix = "S"
    defaultsuffix = "server"
    defaulthost = "*"
    default_flag_log_file = True

    def __init__(self, *args, sleepinterval=0.01, **kwargs):
        super().__init__(*args, **kwargs)
        # time to sleep at each cycle of the main server loop (seconds)
        self.sleepinterval = sleepinterval


class _WithHistory:
    """This is a partial class for ClientConfig and ConsoleConfig."""

    @property
    def historypath(self):
        """Returns the path to the history file."""
        return os.path.join(self.datadir, "history", f"{self.subappname}{self.dash_suffix_or_not()}.history")


class ClientConfig(ClientServerConfig, _WithHistory):
    """Configuration for clients.

    Introduces the concept of "own identity", as a client may assume the subappname and description of
    the server, or use own subappname and description.

    Also now consoles and clients have "favourites" ability

    Args:
        flag_ownidentify:
        fav: favourites list
    """

    loggingprefix = "C"
    defaultsuffix = "client"
    defaulthost = "127.0.0.1"
    default_flag_log_file = False

    def __init__(self, *args, flag_ownidentity=False, fav=None, **kwargs):
        super().__init__(*args, **kwargs)
        if fav is None: fav = []
        self.fav = fav
        self.flag_ownidentity = flag_ownidentity


class ConsoleConfig(BaseConfig, _WithHistory):
    """Configuration for consoles.

    Now consoles and clients have "favourites" ability

    Args:
        fav: favourites list
    """

    loggingprefix = "O"
    defaultsuffix = "console"
    default_flag_log_file = False

    def __init__(self, *args, fav=None, **kwargs):
        super().__init__(*args, **kwargs)
        if fav is None: fav = []
        self.fav = fav
