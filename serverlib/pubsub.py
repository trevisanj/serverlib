__all__ = ["subscriber", "Publisher"]

import zmq, zmq.asyncio, serverlib as sl
from colored import fg, bg, attr


def print_wow(s):
    """Used by the subscription loop to distinguish its output from others' shit."""
    print(f"{attr('bold')+fg('light_yellow')}{s}{attr('reset')}")


class Publisher(sl.Intelligence):
    def __init__(self, master, url):
        super().__init__(master)
        self.url = url

    async def initialize(self):
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.PUB)
        logmsg = f"Binding socket (PUB) to {self.url} ..."
        self.logger.info(logmsg)
        if self.cfg is None or not hasattr(self.cfg, "flag_log_console") or not self.cfg.flag_log_console:
            print(logmsg) # If not logging to console, prints sth anyway (helps a lot)
        self.socket.bind(self.url)

    async def close(self):
        print("Closing PUB server <<<<<<<<<<<<<<<<<<")
        self.logger.debug("Closing PUB server <<<<<<<<<<<<<<<<<<")
        self.socket.close()
        self.context.destroy()

    async def publish(self, msg):
        self.logger.debug(f"PPPPPPPPPPPPPPPPPublishing '{msg}'")
        await self.socket.send_string(msg)


async def subscriber(url, subscriptions):
    """ZMQ SUB client.

    Example:

    >>> def main():
    >>>     url = f"tcp://localhost:9999"
    >>>     async for msg in subscriber(url, ["beep", "print"]):
    >>>         print(f"Received '{msg}')
    """

    print_wow("subscriber() is alive")
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.SUB)
    try:
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
