__all__ = ["Status"]

from dataclasses import dataclass
from typing import Any

@dataclass
class Status:
    """Use this as result of commands when you want to return some message along with the result value."""
    ret: Any = None
    msg: Any = ""

    # What you would like Yoda to say instead of his usual nonsense (handled by Console).
    yoda: str = None
