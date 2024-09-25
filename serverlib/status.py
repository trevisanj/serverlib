__all__ = ["Status"]

from dataclasses import dataclass, field
from typing import Any

@dataclass
class Status:
    """Use this as result of commands when you want to return some message along with the result value."""
    ret: Any = field(default=None)
    # message or list of messages
    msg: Any = field(default="")

    # What you would like Yoda to say instead of his usual nonsense (handled by Console).
    yoda: str = field(default=None)
