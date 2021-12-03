__all__ = ["subscriber", "Publisher", "Subscriber"]

import zmq, zmq.asyncio, serverlib as sl, a107, asyncio
from colored import fg, bg, attr


def format_wow(*args):
    """Used by the subscription loop to distinguish its output from others' shit."""
    s = " ".join(args)
    return f"{attr('bold')+fg('light_yellow')}{s}{attr('reset')}"


def print_wow(*args):
    print(format_wow(*args))


class Publisher(sl.Intelligence):
    """Allows access to a 0MQ "pub" socket. publish() expects bytes."""
    def __init__(self, master, hopo):
        super().__init__(master)
        self.hopo = hopo
        self.__lock = asyncio.Lock()

    async def _on_initialize(self):
        self.context = zmq.asyncio.Context()
        sl.lowstate.numcontexts += 1
        self.socket = self.context.socket(zmq.PUB)
        sl.lowstate.numsockets += 1
        url = sl.hopo2url(self.hopo, "*")
        logmsg = f"Binding socket (PUB) to {url} ..."
        self.logger.info(logmsg)
        if self.cfg is None or not hasattr(self.cfg, "flag_log_console") or not self.cfg.flag_log_console:
            print(logmsg)  # If not logging to console, prints sth anyway (helps a lot)
        self.socket.bind(url)

    async def _on_close(self):
        self.logger.debug("Closing PUB server <<<<<<<<<<<<<<<<<<")
        self.socket.close()
        sl.lowstate.numsockets -= 1
        self.context.destroy()
        sl.lowstate.numcontexts -= 1

    async def publish(self, msg):
        """Publishes message.

        This routine uses a lock in order to allow a single publisher to be shared by several concurrent tasks
        """
        assert isinstance(msg, bytes), "Message must be bytes here"
        try:
            self.logger.debug(f"PPPPPPPPPPPPPPPPPublishing '{msg.decode()}'")
        except UnicodeDecodeError:
            self.logger.debug(f"PPPPPPPPPPPPPPPPPublishing sth; unfortumately IT CAN'T BE SHOWN HERE BECAUSE THERE ARE CHILDREN WATCHING!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        async with self.__lock:
            await self.socket.send(msg)


async def subscriber(hopos, topics, logger=None):
    """ZMQ SUB client implemented as a single async generator

    Example:

    >>> def main():
    >>>     async for msg in subscriber(("localhost", 9999), ["beep", "print"]):
    >>>         print(f"Received '{msg}')
    """
    if logger is None: logger = a107.get_python_logger()
    logger.debug(format_wow("subscriber() is alive"))
    if isinstance(hopos, (int, str)):
        hopos = [hopos]
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.SUB)
    try:
        for hopo in hopos:
            url = sl.hopo2url(hopo)
            logger.debug(format_wow(f"Connecting to {url}..."))
            socket.connect(url)
        for topic in topics:
            if isinstance(topic, str): topic = topic.encode()
            logger.debug(format_wow(f"Subscribing to '{topic}'"))
            socket.setsockopt(zmq.SUBSCRIBE, topic)
        while True:
            logger.debug(format_wow("Waiting for message..."))
            msg = await socket.recv()
            logger.debug(format_wow(f":) Received '{msg}'"))
            yield msg
    finally:
        socket.close()
        context.destroy()
        logger.debug(format_wow("subscriber() says bye"))


class Subscriber:
    """ZMQ SUB client.

    If you have a pre-determined list of topics to subscribe to, you may consider using subscriber() (which is more
    straight-to-the-point).

    However, if you need to change topics, then this class is the resource for you.

    Example:

    >>> def main():
    >>>     async for msg in Subscriber(("localhost", 9999), ["beep", "print"]).agenerator():
    >>>         print(f"Received '{msg}')
    """

    def __init__(self, hopos, topics=None, logger=None):
        self.__flag_stop = False
        if isinstance(hopos, (int, str)):
            hopos = [hopos]
        self.hopos = hopos
        self.topics = []
        if logger is None: logger = a107.get_python_logger()
        self.logger = logger
        logger.debug(format_wow("subscriber() is alive"))

        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.SUB)
        sl.lowstate.numsockets += 1

        for hopo in hopos:
            url = sl.hopo2url(hopo)
            logger.debug(format_wow(f"Connecting to {url}..."))
            self.socket.connect(url)

        if topics: self.subscribe(topics)

    def stop(self):
        """Causes agenerator() to exit."""
        self.__flag_stop = True

    def subscribe(self, topics):
        if isinstance(topics, str): topics = topics.encode()
        if isinstance(topics, bytes): topics = [topics]
        for topic in topics:
            if isinstance(topic, str): topic = topic.encode()
            self.logger.debug(format_wow(f"Subscribing to '{topic}'"))
            self.socket.setsockopt(zmq.SUBSCRIBE, topic)
        self.topics = list(set(self.topics).union(topics))

    def unsubscribe(self, topics):
        if isinstance(topics, str): topics = topics.encode()
        if isinstance(topics, bytes): topics = [topics]
        for topic in topics:
            if isinstance(topic, str): topic = topic.encode()
            self.logger.debug(format_wow(f"Unsubscribing from '{topic}'"))
            self.socket.setsockopt(zmq.UNSUBSCRIBE, topic)
        self.topics = list(set(self.topics)-set(topics))

    def set_topics(self, topics):
        if isinstance(topics, str): topics = topics.encode()
        if isinstance(topics, bytes): topics = [topics]
        for topic in topics:
            if isinstance(topic, str): topic = topic.encode()
            if topic not in self.topics:
                self.subscribe(topic)
        for topic in self.topics:
            if topic not in topics:
                self.unsubscribe(topic)

    async def close(self):
        self.socket.close()
        sl.lowstate.numsockets -= 1
        self.context.destroy()
        self.logger.debug(format_wow("subscriber() says bye"))

    async def agenerator(self):
        logger = self.logger
        logger.debug(format_wow("subscriber() is alive"))
        while not self.__flag_stop:
            logger.debug(format_wow("Waiting for message..."))
            msg = await self.socket.recv()
            logger.debug(format_wow(f":) Received '{msg[:msg.index(b' ')].decode()} ...'"))
            yield msg
