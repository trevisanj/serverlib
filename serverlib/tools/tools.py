__all__ = ["cli_with_hopo", "start_if_not", "stop_if", "cli_start_stop"]

import argparse, serverlib as sl, asyncio, a107, subprocess


def cli_with_hopo(client_or_cfg):
    """Runs a client command-line interface (CLI) with --host and --port/-p arguments.

    Args:
        client_or_cfg: either:
           A) serverlib.Client instance
           B) serverlib.Client subclass
           C) or serverlib.ClientConfig instance
    """

    client, cfg = _get_client_and_cfg(client_or_cfg)

    defaulthost = "127.0.0.1"
    try:
        defaulthost = cfg.defaulthost
    except AttributeError:
        try:
            if cfg.host is not None:
                defaulthost = cfg.host
        except AttributeError:
            pass

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("--host", type=str, required=False, default=defaulthost, help="Host")
    parser.add_argument('-p', '--port', type=float, default=cfg.port, required=False, help="Port")
    args = parser.parse_args()
    cfg.host = args.host
    cfg.port = args.port

    asyncio.run(client.run())


def _get_client_and_cfg(client_or_cfg):
    if isinstance(client_or_cfg, sl.Client):
        client = client_or_cfg
        cfg = client.cfg
    elif isinstance(client_or_cfg, sl.ClientConfig):
        cfg = client_or_cfg
        client = sl.Client(cfg=cfg)
    elif issubclass(client_or_cfg, sl.Client):
        if client_or_cfg == sl.Client:
            raise TypeError(f"I need a ClientConfig to instantialize Client")
        client = client_or_cfg()
        cfg = client.cfg
    else:
        raise TypeError(f"client_or_config must be a Client/ClientConfig instance or a Client subclass, "
                        f"not {client_or_cfg.__class__.__name__}")
    return client, cfg


async def start_if_not(script, client):
    """
    Calls script if poke is unsuccessful.

    Returns:
        serverlib.Status(flag_executed, message)
    """
    ret = False
    try:
        client.temporarytimeout = 2000
        await client.execute_server('s_ping')
    except sl.Retry:
        subprocess.Popen([script])
        ret = True
    return ret

async def stop_if(client):
    """
    Stop server if running.

    Returns:
        serverlib.Status(flag_stopped, message)
    """
    ret = False
    try:
        client.temporarytimeout = 2000
        await client.execute_server('s_ping')
        await client.execute_server("s_stop")
        ret = True
    except sl.Retry:
        pass
    return ret


async def cli_start_stop(client_or_cfg, script):
    """Runs a command-line interface (CLI) with start/stop/restart commands

    Args:
        client_or_cfg: see cli_with_hopo()
        script: server script filename
    """

    client, cfg = _get_client_and_cfg(client_or_cfg)

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

