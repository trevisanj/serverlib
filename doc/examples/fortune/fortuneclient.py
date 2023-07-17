#!/usr/bin/env python
import serverlib, a107, argparse, asyncio

__doc__ = "Fortune Client"


if __name__ == "__main__":
    cfg = serverlib.ClientConfig(appname="fortune",
                                 port=6666,
                                 flag_log_file=False,
                                 flag_log_console=True)

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("--host", type=str, required=False, default=cfg.defaulthost,
                        help="Host: setting this option allows to connect to a different host")
    parser.add_argument('-p', '--port', type=float, default=cfg.port, required=False, help="Port")
    parser.add_argument("command", nargs="?", default=None, help="Command: executes and exits")
    args = parser.parse_args()
    cfg.host = args.host
    cfg.port = args.port

    client = serverlib.Client(cfg)

    if args.command:
        async def run_single_command():
            try:
                res = await client.execute(args.command)
                client.print_last_result(res)
            finally:
                await client.close()
        asyncio.run(run_single_command())
    else:
        asyncio.run(client.run())

