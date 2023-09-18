#!/usr/bin/env python
import serverlib as sl, a107, argparse, asyncio
__doc__ = "Achievements Client"


if __name__ == "__main__":
    cfg = sl.ClientCfg(port=6668,
                          appname="achievements",
                          datadir=".",
                          flag_log_file=True,
                          flag_log_console=False,
                          description=__doc__)

    client = sl.Client(cfg)
    sl.cli_client(client)