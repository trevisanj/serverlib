"""
Miscellaneous routines that are part of serverlib itself, but may be used externally as well
"""

__all__ = ["retry_on_cancelled", "get_client_and_cfg", "get_server_and_cfg", "SCPair", "get_dataroot"]

import asyncio, a107, os
import serverlib as sl


async def retry_on_cancelled(coro, maxtries=10, logger=None):
    """I created this to be used inside 'finally:' blocks in order to force cleaning-up code to be executed.

    Sometimes, I was seeing asyncio.CancelledError being thrown when I was "awaiting on" async methods inside the
    'finally:' block. This was happening when the main-block code got cancelled. So, it fell in the 'finally:' block
    due to an asyncio.CancelledError and the same error was being thrown again by the asyncio mechanism. I am not sure
    if this was due to my incorrect usage or what...

    (20210830) I am not using this method very much and I am not seeing this happening recently, as actually I am
    always succeeding already at the first attempt, apparently."""
    numtries = 1
    while True:
        try:
            await coro
            logger.debug(f"awaiting on {coro} attempt {numtries}/{maxtries} succeeded")
            return
        except asyncio.CancelledError:
            flag_raise = numtries >= maxtries
            if logger is None:
                logger = a107.get_python_logger()
            logger.debug(f"awaiting on {coro} attempt {numtries}/{maxtries} got cancelled"
                         f"({'re-raising Cancelled error' if flag_raise else 'retrying'})")
            if flag_raise: raise
            numtries += 1


def get_client_and_cfg(client_or_cfg):
    """
    Versatile routine to obtain a client instance

    Args:
        client_or_cfg: client class, client instance, or config instance

    Return:
        client, cfg, flag_instantiated
    """
    flag_instantiated = False
    if isinstance(client_or_cfg, sl.Client):
        client = client_or_cfg
        cfg = client.cfg
    elif isinstance(client_or_cfg, sl.ClientConfig):
        cfg = client_or_cfg
        client = sl.Client(cfg=cfg)
        flag_instantiated = True
    elif issubclass(client_or_cfg, sl.Client):
        if client_or_cfg == sl.Client:
            raise TypeError(f"I need a ClientConfig to instantialize Client")
        client = client_or_cfg()
        cfg = client.cfg
        flag_instantiated = True
    else:
        raise TypeError(f"client_or_config must be a Client/ClientConfig instance or a Client subclass, "
                        f"not {client_or_cfg.__class__.__name__}")
    return client, cfg, flag_instantiated


def get_server_and_cfg(server_or_cfg):
    """
    Versatile routine to obtain a server instance

    Args:
        server_or_cfg: server class, server instance, or config instance

    Return:
        server, cfg, flag_instantiated
    """
    flag_instantiated = False
    if isinstance(server_or_cfg, sl.Server):
        server = server_or_cfg
        cfg = server.cfg
    elif isinstance(server_or_cfg, sl.ServerConfig):
        cfg = server_or_cfg
        server = sl.Server(cfg=cfg)
    elif issubclass(server_or_cfg, sl.Server):
        if server_or_cfg == sl.Server:
            raise TypeError(f"I need a ServerConfig to instantialize Server")
        server = server_or_cfg()
        cfg = server.cfg
        flag_instantiated = True
    else:
        raise TypeError(f"server_or_config must be a Server/ServerConfig instance or a Server subclass, "
                        f"not {server_or_cfg.__class__.__name__}")
    return server, cfg, flag_instantiated


class SCPair:
    """Server-Client Pair"""
    def __init__(self, server_or_cfg, client_or_cfg):
        self.server, self.servercfg, self.flag_instantiated_server = get_server_and_cfg(server_or_cfg)
        self.client, self.clientcfg, self.flag_instantiated_client = get_client_and_cfg(client_or_cfg)


def get_dataroot():
    """
    Returns serverlib dataroot

    Dataroot may be defined by environment variable or internal default (see serverlib.config module).
    """

    dataroot = os.getenv(sl.config.datarootenvvar)
    if not dataroot:
        dataroot = sl.config.defaultdataroot
    if "~" in dataroot:
        dataroot = os.path.expanduser(dataroot)
    return dataroot