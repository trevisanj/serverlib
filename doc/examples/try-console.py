#!/usr/bin/env python
"""
Instantializes serverlib.Console for fun
"""

import serverlib as sl, asyncio

if __name__ == "__main__":
    cfg = sl.ConsoleConfig(appname="try-console")
    console = sl.Console(cfg)

    asyncio.run(console.run())