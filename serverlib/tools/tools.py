__all__ = ["cli_client", "cli_server", "start_if_not", "stop_if", "cli_start_stop"]

import argparse, serverlib as sl, asyncio, a107, subprocess


def cli_client(client_or_cfg):
    """
    Runs a client command-line interface (CLI) with --host and --port/-p arguments.

    Args:
        client_or_cfg: either:
           A) serverlib.Client instance
           B) serverlib.Client subclass
           C) or serverlib.ClientConfig instance
    """

    client, cfg, _ = __get_client_and_cfg(client_or_cfg)

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("--host", type=str, required=False, default=cfg.defaulthost,
                        help="Host: setting this options allows to connect to a different host")
    parser.add_argument('-p', '--port', type=float, default=cfg.port, required=False, help="Port")
    args = parser.parse_args()
    cfg.host = args.host
    cfg.port = args.port

    asyncio.run(client.run())

def cli_server(server_or_cfg):
    """
    Runs a server command-line interface (CLI) with --host and --port/-p arguments.

    Args:
        server_or_cfg: either:
           A) serverlib.Server instance
           B) serverlib.Server subclass
           C) or serverlib.ServerConfig instance
    """

    server, cfg = __get_server_and_cfg(server_or_cfg)

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("--host", type=str, required=False, default=cfg.defaulthost,
                        help="Host: setting this option allows to bind to a different host")
    parser.add_argument('-p', '--port', type=float, default=cfg.port, required=False, help="Port")
    args = parser.parse_args()
    cfg.host = args.host
    cfg.port = args.port

    asyncio.run(server.run())


async def start_if_not(script, client_or_cfg):
    """
    Calls script if poke is unsuccessful.

    Returns:
        serverlib.Status(flag_executed, message)
    """
    ret = False
    client, _, flag_instantialized = __get_client_and_cfg(client_or_cfg)
    try:
        client.temporarytimeout = 2000
        await client.execute_server('s_ping')
    except sl.Retry:
        subprocess.Popen([script])
        ret = True
    finally:
        if flag_instantialized:
            await client.close()
    return ret

async def stop_if(client_or_cfg):
    """
    Stop server if running.

    Returns:
        serverlib.Status(flag_stopped, message)
    """
    ret = False
    client, _, flag_instantialized = __get_client_and_cfg(client_or_cfg)
    try:
        client.temporarytimeout = 2000
        await client.execute_server('s_ping')
        await client.execute_server("s_stop")
        ret = True
    except sl.Retry:
        pass
    finally:
        if flag_instantialized:
            await client.close()
    return ret


async def cli_start_stop(client_or_cfg, script):
    """Runs a command-line interface (CLI) with start/stop/restart commands

    Args:
        client_or_cfg: see cli_with_hopo()
        script: server script filename
    """

    client, cfg, _ = __get_client_and_cfg(client_or_cfg)

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("command", choices=["start", "stop", "restart"])
    args = parser.parse_args()

    flag_start = args.command in ("start", "restart")
    flag_stop = args.command in ("stop", "restart")

    s_script = f"Script '{script}'"
    if flag_stop:
        ret = await stop_if(client)
        if ret:
            print(f"{s_script} was stopped")
        else:
            print(f"{s_script} was not stopped, as it was not running")
    if flag_start:
        ret = await start_if_not(script, client)
        if ret:
            print(f"{s_script} was started")
        else:
            print(f"{s_script} was not started, as it is already running")



def __get_client_and_cfg(client_or_cfg):
    flag_instantialized = False
    if isinstance(client_or_cfg, sl.Client):
        client = client_or_cfg
        cfg = client.cfg
    elif isinstance(client_or_cfg, sl.ClientConfig):
        cfg = client_or_cfg
        client = sl.Client(cfg=cfg)
        flag_instantialized = True
    elif issubclass(client_or_cfg, sl.Client):
        if client_or_cfg == sl.Client:
            raise TypeError(f"I need a ClientConfig to instantialize Client")
        client = client_or_cfg()
        cfg = client.cfg
        flag_instantialized = True
    else:
        raise TypeError(f"client_or_config must be a Client/ClientConfig instance or a Client subclass, "
                        f"not {client_or_cfg.__class__.__name__}")
    return client, cfg, flag_instantialized


def __get_server_and_cfg(server_or_cfg):
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
    else:
        raise TypeError(f"server_or_config must be a Server/ServerConfig instance or a Server subclass, "
                        f"not {server_or_cfg.__class__.__name__}")
    return server, cfg
