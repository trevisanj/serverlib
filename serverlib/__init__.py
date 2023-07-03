from . import consts
from .errors import *
from .lowstate import *
from .configclasses import *
from .serverlibapi import *
from .intelligence import *
from .commands import *
from .console import *
from .client import *
from .server import *
from .tools import *
from .basicservercommands import *
from .pubsub import *
from .embedding import *
from .waiter import *

# Whether to server-side log traceback when command raises exception (to help with debugging)
flag_log_traceback = True

# Time to wait before retrying. This value is "informed" by a raised Retry exception
retry_waittime = 1.

# Default configuration for serverlib.Waiter instances
waiter_waittime = 0.5     # initial waiting time
waiter_waittime_max = 30  # maximum waiting time
waiter_maxtries = 10      # maximum number of attempts

