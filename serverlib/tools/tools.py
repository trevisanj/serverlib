__all__ = ["cli_with_hopo"]

import argparse, serverlib as sl, asyncio, a107

def cli_with_hopo(config, clientcls=None):
    """Runs a client command-line interface (CLI) with --host and --port/-p arguments.

    clientcls is instantiated without arguments. It is assumed that it internally uses the config object.
    """
    if clientcls is None: clientcls = lambda: sl.Client(config)
    defaulthost = "127.0.0.1"
    try: defaulthost = config.defaulthost
    except AttributeError:
        try:
            if config.host is not None: defaulthost = config.host
        except AttributeError:pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("--host", type=str, required=False, default=defaulthost, help="Host")
    parser.add_argument('-p', '--port', type=float, default=config.port, required=False, help="Port")
    args = parser.parse_args()
    config.host = args.host
    config.port = args.port
    client = clientcls()
    asyncio.run(client.run())

