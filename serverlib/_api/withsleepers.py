__all__ = ["WithSleepers"]

import asyncio, a107
from dataclasses import dataclass
from typing import Any


class WithSleepers:

    @property
    def sleepers(self):
        return self.__sleepers

    def __init__(self):
        self.__sleepers = {}  # {name: _Sleeper, ...}

    def wake_up(self, sleepername=None):
        """Cancel all "naps" created with self.sleep(), or specific one specified by sleepername."""
        if sleepername is not None:
            self.__sleepers[sleepername].flag_wake_up = True
        else:
            for sleeper in self.__sleepers.values(): sleeper.flag_wake_up = True

    async def wait_a_bit(self):
        """Unified way to wait for a bit, usually before retrying something that goes wront."""
        await self.sleep(0.1)

    async def sleep(self, waittime, name=None):
        """
        Async blocks for waittime seconds, with possibility of premature wake-up using wake_up() method.

        Args:
            waittime: value in seconds
            name: optional, unique name. If a sleeper with name already exists, will raise error.
                  If not passed, will create a random name for the sleeper
        """

        if name is None:
            name = a107.random_name()
            while name in self.__sleepers:
                name = a107.random_name()
        else:
            if name in self.__sleepers:
                raise RuntimeError(f"Sleeper '{name}' already exists")

        my_debug = lambda s: logger.debug(
            f"😴 {self.__class__.__name__}.sleep() {sleeper.name} {waittime:.3f} seconds {s}")
        logger = self.logger
        interval = min(waittime, 0.1)

        sleeper = _Sleeper(waittime, name)
        self.__sleepers[sleeper.name] = sleeper
        slept = 0
        try:
            my_debug("💤💤💤")
            while slept < waittime and not sleeper.flag_wake_up:
                await asyncio.sleep(interval)
                slept += interval
        finally:
            my_debug("⏰ Wake up!")
            try:
                del self.__sleepers[sleeper.name]
            except KeyError:
                pass

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

@dataclass
class _Sleeper:
    seconds: int
    name: str
    task: Any = None
    flag_wake_up: bool = False
