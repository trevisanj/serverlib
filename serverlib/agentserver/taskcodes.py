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




# import serverlib as sl


# actiondescriptions = {
#     ACTION_CELEBRATE: "celebrate",
#     ACTION_RETRY: "retry",
#     ACTION_SUSPEND: "suspend",
#     ACTION_CRASH: "crash",
# }

# # In case some exceptions are subclasses of one another, the more specific ones must come first
# resultmap = {
# RESULT_SUCCESS:
#     {"result": RESULT_SUCCESS,
#      "description": "success",
#      "emoji": "🥂",
#      "action": ACTION_CELEBRATE,
#      "exception": None},
# RESULT_TOO_FAST:
#     {"result": RESULT_TOO_FAST,
#      "description": "too fast",
#      "emoji": "↺",
#      "action": ACTION_RETRY,
#      "exception": sacca.TooFast},
# RESULT_RETRY:
#     {"result": RESULT_RETRY,
#      "description": "retry",
#      "emoji": "↺",
#      "action": ACTION_RETRY,
#      "exception": sl.Retry},
# RESULT_BADSYMBOL:
#     {"result": RESULT_BADSYMBOL,
#      "description": "bad symbol",
#      "emoji": "💩",
#      "action": ACTION_SUSPEND,
#      "exception": sacca.BadSymbol},
# RESULT_BUG:
#     {"result": RESULT_BUG,
#      "description": "bug",
#      "emoji": "🐞",
#      "action": ACTION_CRASH,
#      "exception": BaseException},
# }
#
# def taskexceptions():
#     return tuple(row["exception"] for row in resultmap.values() if row["exception"])
#
# del sacca, sl