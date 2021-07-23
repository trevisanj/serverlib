"""Low-level, application-level variables.

This was created for debugging purposes and may  be accessed through
"""

__all__ = ["lowstate"]

from dataclasses import dataclass


@dataclass
class LowState:
    numsockets: int = 0
    numcontexts: int = 0


lowstate = LowState()