__all__ = ["subscriber", "Publisher"]

import zmq, zmq.asyncio, serverlib as sl
from colored import fg, bg, attr


def print_wow(s):
    """Used by the subscription loop to distinguish its output from others' shit."""
    print(f"{attr('bold')+fg('light_yellow')}{s}{attr('reset')}")


class Publisher(sl.Intelligence):
    def __init__(self, master, hopo):
        super().__init__(master)
        self.hopo = hopo

    async def initialize(self):
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.PUB)
        url = sl.hopo2url(self.hopo, "*")
        logmsg = f"Binding socket (PUB) to {url} ..."
        self.logger.info(logmsg)
        if self.cfg is None or not hasattr(self.cfg, "flag_log_console") or not self.cfg.flag_log_console:
            print(logmsg) # If not logging to console, prints sth anyway (helps a lot)
        self.socket.bind(url)

    async def close(self):
        print("Closing PUB server <<<<<<<<<<<<<<<<<<")
        self.logger.debug("Closing PUB server <<<<<<<<<<<<<<<<<<")
        self.socket.close()
        self.context.destroy()

    async def publish(self, msg):
        self.logger.debug(f"PPPPPPPPPPPPPPPPPublishing '{msg}'")
        await self.socket.send_string(msg)


async def subscriber(hopos, subscriptions):
    """ZMQ SUB client.

    Example:

    >>> def main():
    >>>     async for msg in subscriber(("localhost", 9999), ["beep", "print"]):
    >>>         print(f"Received '{msg}')
    """
    print_wow("subscriber() is alive")
    if isinstance(hopos, (int, str)):
        hopos = [hopos]
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.SUB)
    try:
        for hopo in hopos:
            url = sl.hopo2url(hopo)
            print_wow(f"Connecting to {url}...")
            socket.connect(url)
        for topic in subscriptions:
            print_wow(f"Subscribing to '{topic}")
            socket.setsockopt_string(zmq.SUBSCRIBE, topic)
        while True:
            print_wow("Waiting for message...")
            msg = (await socket.recv()).decode()
            print_wow(f":) Received '{msg}'")
            yield msg
    finally:
        socket.close()
        context.destroy()
        print_wow("subscriber() says bye")
