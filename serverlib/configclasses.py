"""BaseConfig class"""

__all__ = ["BaseConfig", "ServerConfig", "ClientConfig", "ConsoleConfig"]

import os, a107, configobj, serverlib as sl, random
import traceback

from . import config, _api

class BaseConfig:
    """Common functionality for ClientConfig and ServerConfig.

    Implements certain conventions on directories, configuration and log filenames based on the application name, see
    properties.

    Args:
        appname: "umbrella" name affecting self.autodir=="~/.<appname>"
        flag_log_file:
        flag_log_console:
        level:
        datadir:
        subappname: Used in filenames and welcome message
        scc: "server", "client" or "console". Can be customized
        description:
        cfg: another BaseConfig. If passed, appname and subappname will be taken from this cfg.
             It has precedence over appname and subappname passed as arguments

    Howto:

        - add configurable attribute: override __init__()
    """


    # Prefix in logging messages to distinguish client from server
    loggingprefix = ""

    # Suffix to show on certain occasions
    defaultscc = ""

    @property
    def autodir(self):
        """Automatic directory made from self.appname."""
        if self.__autodir is None:
            self.__autodir = self.__make_autodir()
        return self.__autodir

    @property
    def subappname(self):
        return self.__subappname if self.__subappname is not None else self.appname

    @property
    def scc(self):
        return self.__scc if self.__scc is not None else self.defaultscc

    @scc.setter
    def scc(self, value):
        self.__scc = value

    @property
    def datadir(self):
        return self.__datadir if self.__datadir is not None else self.autodir

    @datadir.setter
    def datadir(self, value):
        self.__datadir = value

    @property
    def reportdir(self):
        ret = os.path.join(self.datadir, "reports")
        return ret

    @property
    def configdir(self):
        ret = os.path.join(self.datadir, "cfg")
        return ret

    @property
    def configfilename(self):
        filename = f"{self.subappname}{self.dash_suffix_or_not()}.cfg"
        return filename

    @property
    def configpath(self):
        ret = os.path.join(self.configdir, self.configfilename)
        return ret

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
                 flag_log_file=None,
                 flag_log_console=None,
                 datadir=None,
                 logginglevel=None,
                 subappname=None,
                 scc=None,
                 description=None,
                 cfg=None,
                 ):
        # possible error when subclassing
        assert self.defaultscc is not None, f"Forgot to set {self.__class__.__name__}.defaultscc"

        self.flag_log_file = flag_log_file if flag_log_file is not None else sl.config.logging.flag_file
        self.flag_log_console = flag_log_console if flag_log_console is not None else sl.config.logging.flag_console
        self.logginglevel = logginglevel if logginglevel is not None else sl.config.logging.level

        if cfg is not None:
            appname = cfg.appname
            subappname = cfg.subappname

        assert appname is not None, "appname has not been assigned either explicitly or with cfg"

        self.appname = appname
        self.description = description
        self.__datadir = datadir
        self.__subappname = subappname
        self.__scc = scc

        self.master = None  # Server or Client
        self.__logger = None
        self.__autodir = None

    def __str__(self):
        return sl.cfg2str(self)

    def dash_suffix_or_not(self, suffix=None):
        """Eventually prefixes suffix with a "-"

        Args:
            suffix: defaults to self.scc

        Returns:
            "-"+(suffix or self.scc), or ""

            a) if suffix is empty, returns ""
            b) if suffix starts with ".", does not precede suffix with a "-"
            c) if suffix is not empty and does not start with a (".", "-"), precedes it with a "-"
        """
        if suffix is None:
            suffix = self.scc
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
        if a107.ensure_path(d):
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
        """Makes path <datadir>/<subappname><suffix>.

        Example of suffix: "-vars.pickle"
        """
        return os.path.join(self.datadir, f"{self.subappname}{self.dash_suffix_or_not(suffix)}")

    def get_welcome(self):
        slugtitle = f"Welcome to the '{self.subappname}' {self.scc}"
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
            if a107.ensure_path(d):
                self.logger.info(f"Created directory '{d}'")
            ret = self.__get_configobj_with_path(configpath, True)
        return ret

    def __make_autodir(self):
        dataroot = os.getenv(sl.config.datarootenvvar)
        # todo cleanup can't use logger here, so had to print print("\n\n\n\n\n===============  LASQUEIRAAAAAAAAAAAA", self.subappname, sl.config.datarootenvvar, dataroot)
        #  traceback.print_stack()
        #  print("=================\n")
        if not dataroot:
            dataroot = sl.config.defaultdataroot
        if "~" in dataroot:
            dataroot = os.path.expanduser(dataroot)
        ret = os.path.join(dataroot, self.appname)
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
    defaultscc = "server"
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
    defaultscc = "client"
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
    defaultscc = "console"
    default_flag_log_file = False

    def __init__(self, *args, fav=None, **kwargs):
        super().__init__(*args, **kwargs)
        if fav is None: fav = []
        self.fav = fav
