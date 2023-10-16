"""
Definition of possible values for some of the task fields.

Q: Why are task code classes not Python Enum?
A: The codes are recorded as strings in the db file, and comparisons are cleaner like this.
   If they were enums: (task.state == TaskState.idle.value)
"""
__all__ = ["TaskState", "TaskResult", "TaskAction", "errormap", "ErrorMapItem", "prepend_item"]

from dataclasses import dataclass
from typing import Any
import serverlib as sl


class TaskState:
    """Possible values for task.state"""
    idle = "idle"
    in_progress = "in_progress"
    suspended = "suspended"
    inactive = "inactive"

class TaskResult:
    """Possible values for task.result"""
    none = "none"
    success = "success"
    fail = "fail"

class TaskAction:
    """Possible actions on error executing task."""
    retry = "retry"
    suspend = "suspend"


@dataclass
class ErrorMapItem:
    # BaseException class
    ecls: Any
    action: str
    flag_raise: bool


errormap = [ErrorMapItem(sl.Retry, TaskAction.retry, False),
            ErrorMapItem(BaseException, TaskAction.suspend, True),
            ]

def prepend_item(item):
    errormap.insert(0, item)
