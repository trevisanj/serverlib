
__all__ = ["retry_on_cancelled"]

import asyncio, a107


async def retry_on_cancelled(coro, maxtries=10, logger=None):
    """I created this to be used inside 'finally:' blocks in order to force cleaning-up code to be executed.

    Sometimes, I was seeing asyncio.CancelledError being thrown when I was "awaiting on" async methods inside the
    'finally:' block. This was happening when the main-block code got cancelled. So, it fell in the 'finally:' block
    due to an asyncio.CancelledError and the same error was being thrown again by the asyncio mechanism. I am not sure
    if this was due to my incorrect usage or what...

    (20210830) I am not using this method very much and I am not seeing this happening recently, as actually I am
    always succeeding already at the first attempt, apparently."""
    numtries = 1
    while True:
        try:
            await coro
            logger.debug(f"awaiting on {coro} attempt {numtries}/{maxtries} succeeded")
            return
        except asyncio.CancelledError:
            flag_raise = numtries >= maxtries
            if logger is None:
                logger = a107.get_python_logger()
            logger.debug(f"awaiting on {coro} attempt {numtries}/{maxtries} got cancelled"
                         f"({'re-raising Cancelled error' if flag_raise else 'retrying'})")
            if flag_raise: raise
            numtries += 1

