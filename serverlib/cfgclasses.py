"""
All serverlib "cfg" classes in one file.

Attributes starting with "_" ("protected") are not written to configuration file.

All time values are in seconds.
"""

__all__ = ["BaseCfg", "ConsoleCfg", "ServerCfg", "ClientCfg", "AgentCfg"]

import logging


class BaseCfg:
    """Base class for all "cfg" objects"""
    _appname = None
    _subappname = None
    logginglevel = logging.INFO
    flag_log_console = True
    flag_log_file = True


class ConsoleCfg(BaseCfg):
    pass


class ServerCfg(BaseCfg):
    host = "*"
    port = None
    # time to sleep at each server main loop cycle
    sleepinterval = 0.01


class ClientCfg(BaseCfg):
    host = "127.0.0.1"
    # time waiting to send to and receive from server (in practice the total wait time is 2*timeout)
    timeout = 30


class AgentCfg(ServerCfg):
    # interval to review all tasks and spawn/kill agents
    agentloopinterval = 15
    # time to wait before retrying a failed task
    retry_waittime = 1




