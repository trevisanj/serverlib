#!/usr/bin/env python
import serverlib, a107, argparse, asyncio
__doc__ = "Fortune Client"

def main(args):
    cfg = serverlib.ClientConfig()
    cfg.host = args.host
    cfg.port = args.port
    cfg.applicationname = "fortune"
    cfg.flag_log_file = True
    cfg.flag_log_console = False
    cfg.description = __doc__

    client = serverlib.Client(cfg)
    asyncio.run(client.run())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("--host", type=str, help="host", default="127.0.0.1")
    parser.add_argument('port', type=int, help='port', nargs="?", default=6666)
    parser.add_argument('statement', type=str, help='statement to execute and exit afterwards', nargs="*", default=[])

    args = parser.parse_args()
    main(args)
