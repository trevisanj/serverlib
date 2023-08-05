"""
Routines not used by serverlib itself (made for external use!)

If you start using anything here within serverlib, move to basicapi.py instead
"""

__all__ = ["cli_client", "cli_server", "start_if_not", "stop_if", "cli_start_stop", "cli_start_stop1"]

import argparse, serverlib as sl, asyncio, a107, subprocess, sys


def cli_client(client_or_cfg):
    """
    Runs a client command-line interface (CLI) with --host and --port/-p arguments.

    Args:
        client_or_cfg: either:
           A) serverlib.Client instance
           B) serverlib.Client subclass
           C) or serverlib.ClientConfig instance
    """

    client, cfg, _ = sl.get_client_and_cfg(client_or_cfg)

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

    server, cfg, _ = sl.get_server_and_cfg(server_or_cfg)

    parser = argparse.ArgumentParser(description="????????????????????????????????????????????????", formatter_class=a107.SmartFormatter)
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
        whether or not started the server
    """
    ret = False
    client, _, flag_instantiated = sl.get_client_and_cfg(client_or_cfg)
    try:
        client.temporarytimeout = 2000
        await client.execute_server('s_ping')
    except sl.Retry:
        subprocess.Popen([script])
        ret = True
    finally:
        if flag_instantiated:
            await client.close()
    return ret

async def stop_if(client_or_cfg):
    """
    Stop server if running.

    Returns:
        whether or not stopped the server
    """
    ret = False
    client, _, flag_instantiated = sl.get_client_and_cfg(client_or_cfg)
    try:
        client.temporarytimeout = 2000
        await client.execute_server('s_ping')
        await client.execute_server("s_stop")
        ret = True
    except sl.Retry:
        pass
    finally:
        if flag_instantiated:
            await client.close()
    return ret


async def cli_start_stop(client_or_cfg, script):
    """Runs a command-line interface (CLI) with start/stop/restart commands

    Args:
        client_or_cfg: see cli_with_hopo()
        script: server script filename
    """

    client, cfg, _ = sl.get_client_and_cfg(client_or_cfg)

    parser = argparse.ArgumentParser(description="??????????????????????????????????????????????????", formatter_class=a107.SmartFormatter)
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


async def cli_start_stop1(server_or_cfg, client_or_cfg):
    """Runs a command-line interface (CLI) with start/stop/restart commands

    Args:
        server_or_cfg: see serverlib.get_server_and_cfg()
        client_or_cfg: see serverlib.get_client_and_cfg()
    """

    async def call_again_run_if_not():
        """Starts server if ping is unsuccessful"""
        flag_started = False
        try:
            client.temporarytimeout = 2000
            await client.execute_server('s_ping')
        except sl.Retry:
            print(sys.argv[0])
            subprocess.Popen([sys.argv[0], "run"])
            flag_started = True
        return flag_started

    client, cfg, flag_instantiated = sl.get_client_and_cfg(client_or_cfg)
    try:

        # Here we are trusting the client to be matchin the server subappname
        servername = cfg.subappname

        description = \
f"""'{servername}' server control

Descriptions of commands:
    start    starts server if not running
    stop     stops server if running
    restart  start+stop combined
    status   ping server
    run      blocking run; does not check if running
"""

        parser = argparse.ArgumentParser(description=description, formatter_class=a107.SmartFormatter)
        parser.add_argument("command", choices=["start", "stop", "restart", "ping", "run"],)
        args = parser.parse_args()

        if args.command == "run":
            # if "--run" option is present, will take a different path and ignore "command"
            server, _, _ = sl.get_server_and_cfg(server_or_cfg)
            await server.run()
        elif args.command == "ping":
            try:
                print(f"Pinging server (timeout={sl.lowstate.timeout/1000:g} seconds)...")
                print(await client.execute_server('s_ping'))
            except (KeyboardInterrupt, asyncio.CancelledError):
                print("Interrupted")
            except sl.Retry:
                print("Ping unsuccessful")
        else:
            flag_start = args.command in ("start", "restart")
            flag_stop = args.command in ("stop", "restart")

            if flag_stop:
                ret = await stop_if(client)
                if ret:
                    print(f"Server '{servername}' was stopped")
                else:
                    print(f"Server '{servername}' was not stopped, as it was not running")
            if flag_start:
                ret = await call_again_run_if_not()
                if not ret:
                    print(f"Server '{servername}' was not started, as it is already running")
    finally:
        if flag_instantiated:
            await client.close()

