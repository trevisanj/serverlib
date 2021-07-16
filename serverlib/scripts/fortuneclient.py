#!/usr/bin/env python
import serverlib, a107, argparse, asyncio
__doc__ = "Fortune Client"

def main(args):
    cfg = serverlib.ClientConfig(appname="fortune",
                                 host = args.host,
                                 port = args.port,
                                 flag_log_file=False,
                                 flag_log_console=True)
    client = serverlib.Client(cfg)
    asyncio.run(client.run())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("--host", type=str, help="host", default="127.0.0.1")
    parser.add_argument('port', type=int, help='port', nargs="?", default=6666)
    parser.add_argument('statement', type=str, help='statement to execute and exit afterwards', nargs="*", default=[])

    args = parser.parse_args()
    main(args)
