"""
Expandable errormap to determine actions
"""
__all__ = ["TaskState", "TaskResult", "TaskAction", "errormap", "ErrorMapItem", "prepend_item"]

from dataclasses import dataclass
from typing import Any
import serverlib as sl


class TaskState:
# sqlite file's task.state possible values
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    SUSPENDED = "suspended"

class TaskResult:
    NONE = "none"
    SUCCESS = "success"
    FAIL = "fail"

class TaskAction:
    """Possible actions on error executing task."""
    RETRY = "retry"
    SUSPEND = "suspend"


@dataclass
class ErrorMapItem:
    # Exception class
    ecls: Any
    action: str
    flag_raise: bool

errormap = [ErrorMapItem(sl.Retry, TaskAction.RETRY, False),
            ErrorMapItem(Exception, TaskAction.SUSPEND, True),
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
#      "exception": Exception},
# }
#
# def taskexceptions():
#     return tuple(row["exception"] for row in resultmap.values() if row["exception"])
#
# del sacca, sl