__all__ = ["Status"]

from dataclasses import dataclass
from typing import Any

@dataclass
class Status:
    """Use this as result of commands when you want to return some message along with the result value."""
    msg: Any = ""
    ret: Any = None
    # What you would like Yoda to day instead of his usual nonsense.
    yoda: str = None
