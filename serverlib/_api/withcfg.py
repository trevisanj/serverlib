__all__ = ["WithCfg"]

import os, a107, configobj, serverlib as sl, random, shelve
import traceback
from serverlib import config
from . import _misc


class WithCfg:
    """
    Common ancestor for Console, Client and Server providing basic configuration features.

    Implements certain conventions on directories, configuration and log filenames based on the application name, see
    properties.

    Args:
        cfg:
        description:
    Howto:

        - add configurable attribute: override __init__()
    """

    # Suffix to show on certain occasions ("server"/"client"/"console")
    whatami: str = ""

    @property
    def description(self):
        """Returns class description or beginning of __doc__ before "Args:"."""
        if self.__description:
            return self.__description
        doc = self.__doc__
        if not doc:
            return ""
        last_is_empty = False
        lines = doc.split("\n")
        i = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("Args"):
                i -= 1+int(last_is_empty)  # does not take blank line before "Args:"
                break
            last_is_empty = len(stripped) == 0
        return "__doc__\n\n"+"\n".join(lines[:i+1])

    @property
    def autodir(self):
        """Automatic directory made from self.appname."""
        if self.__autodir is None:
            self.__autodir = self.__make_autodir()
        return self.__autodir

    @property
    def appname(self):
        return self.cfg._appname

    @property
    def subappname(self):
       return self.cfg._subappname if self.cfg._subappname else self.cfg._appname

    @property
    def datadir(self):
        return self.autodir

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
    def logger(self):
        if self.__logger is None:
            self.__create_logger()

        return self.__logger

    def __init__(self, cfg, description=""):
        self.__description = description
        self.cfg = cfg
        self.master = None
        self.__logger = None
        self.__autodir = None

    def get_welcome(self):
        """Standard welcome message."""
        # LEFT = " * "
        # slugtitle = f"Welcome to the '{self.subappname}' {self.whatami}"
        # ret = "\n".join([f"{LEFT}{x}" for x in a107.format_slug(slugtitle, random.randint(0, 2))])
        # description = self.description
        # if description:
        #     ret += "\n"+a107.kebab("\n"+description, config.descriptionwidth, LEFT)
        # return ret
        slugtitle = f"Welcome to the '{self.subappname}' {self.whatami}"
        _ret = a107.format_slug(slugtitle, fmt=str)
        description = self.description
        if description:
            _ret += "\n"+a107.kebab("\n"+description, config.descriptionwidth)
        ret = a107.format_box(_ret, fmt=str)
        return ret

    def get_new_sublogger(self, namesuffix):
        """Creates new logger with compounded name"""
        return self.get_new_logger(f"{self.logger.name}.{namesuffix}")

    def get_new_logger(self, name):
        """Creates new logger using all the same configuration as self.logger, except name"""

        flag_log_file = self.__get_flag_log_file()
        flag_log_console = self.cfg.flag_log_console if self.cfg.flag_log_console is not None \
            else sl.config.logging.flag_console
        logginglevel = self.cfg.logginglevel if self.cfg.logginglevel is not None else sl.config.logging.level
        ret = _misc.get_new_logger(fn_log=self.logpath,
                                   flag_log_file=flag_log_file,
                                   flag_log_console=flag_log_console,
                                   level=logginglevel,
                                   prefix=config.logging.prefixes[self.whatami],
                                   name=name)
        return ret

    def dash_suffix_or_not(self, suffix=None):
        """Eventually prefixes suffix with a "-"

        Args:
            suffix: defaults to self.whatami

        Returns:
            "-"+(suffix or self.whatami), or ""

            a) if suffix is empty, returns ""
            b) if suffix starts with ".", does not precede suffix with a "-"
            c) if suffix is not empty and does not start with a (".", "-"), precedes it with a "-"
        """
        if suffix is None:
            suffix = self.whatami
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
        """

        self.logger.warning("read_configfile() no longer implemented")
        return

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

    # def get_option(self, attrname, default=None):
    #     """Retrieves attribute with default option."""
    #     return getattr(self, attrname) if hasattr(self, attrname) else default
    #
    # def set_option(self, attrname, value):
    #     """Sets value both as self's attribute and within the config file."""
    #     setattr(self, attrname, value)
    #     h = self.__get_configobj()
    #     h[attrname] = value
    #     h.write()

    def filepath(self, *args):
        """
        Makes path using datadir and automatic filename

        Args: [subdir0, subdir1, ..., suffix]

        Returns:
            ret: path to file

        Example:
            filepath("console", ".history") --> "<datadir>/console/<subappname>.history"
        """
        return os.path.join(self.datadir, *args[:-1], f"{self.subappname}{self.dash_suffix_or_not(args[-1])}")

    def __get_configobj_with_path(self, path_, flag_create_empty):
        """Gets config for specific file path."""

        self.logger.warning("__get_configobj_with_path() no longer implemented")
        return


        flag_exists = os.path.isfile(path_)
        ret = configobj.ConfigObj(path_, create_empty=flag_create_empty, unrepr=True)
        flag_exists_ = os.path.isfile(path_)
        if flag_exists_ != flag_exists:
            self.logger.info(f"Created file '{path_}'")
        return ret

    def __get_configobj(self):
        """Gets config in local path or in configuration directory, whichever is found first."""

        self.logger.warning("__get_configobj() no longer implemented")
        return


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
        dataroot = sl.get_dataroot()
        ret = os.path.join(dataroot, self.appname)
        return ret

    def __create_logger(self):
        """Creates self.__logger. Must be the first logger to be created"""
        flag_created_dir = False
        if self.__get_flag_log_file():
            dir_ = os.path.split(self.logpath)[0]
            if dir_:
                flag_created_dir = a107.ensure_path(dir_)
        self.__logger = self.get_new_logger(self.subappname)
        if flag_created_dir:
            self.__logger.info(f"Created directory '{dir_}'")

    def __get_flag_log_file(self):
        return self.cfg.flag_log_file if self.cfg.flag_log_file is not None \
            else sl.config.logging.flag_file
