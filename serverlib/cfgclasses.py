"""
All serverlib "cfg" classes.

Notes:
    1. **These classes are not made to be instantiated!**
    2. Attributes starting with "_" ("protected") are not written to configuration file
    3. All time values are in seconds
"""

__all__ = ["BaseCfg", "ConsoleCfg", "ServerCfg", "ClientCfg", "AgentCfg"]

import logging


class BaseCfg:
    """Base class for all "cfg" objects"""

    _appname = None
    _subappname = None
    # logging configuration is set to None so that WithCfg.__create_logger() will take defaults
    logginglevel = None
    flag_log_console = None
    flag_log_file = None


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
    # time to wait before retrying a retriable command (i.e. when serverlib.Retry is raised)
    waittime_retry_command = .1
    # maximum number of retries for a retriable command
    maxtries = 3


class AgentCfg(ServerCfg):
    # interval to review all tasks and spawn/kill agents
    agentloopinterval = 15
    # time to wait before retrying a failed task
    waittime_retry_task = 1.
    # time to wait if agent found no tasks to execute
    waittime_no_tasks = 10.




