import _thread
import sys
import time

from . import tstate, ctypes_defs
from . import errors
from . import *


RANDOM_KEYBOARD_INTERRUPT = False
try:
    import signal as _s
except ImportError:
    RANDOM_KEYBOARD_INTERRUPT = True
"""
The _thread docs warn us that when the signal module is
not available, and the process is interrupted, an arbitrary thread 
will receive KeyboardInterrupt.
See the 'Caveats' section on the docs:
https://docs.python.org/3/library/_thread.html
"""


def start(activity, args, kwargs={}):
    sys.audit(f"{__ROOT__}.thread.start", activity)

    state = tstate.ThreadState.__new__(tstate.ThreadState)
    args = list(args)
    args.insert(0, state)
    th = _thread.start_new_thread(activity, tuple(args), kwargs)
    state._id = th
    # print('this one:')
    state.__init__()
    return state


def join(th, timeout=None):
    sys.audit(f"{__ROOT__}.thread.join", th)
    if th.id == _thread.get_native_id():
        raise errors.ContextError("Threads cannot join themselves.") from errors.configure(1)

    if th._alive_lock is None:
        start_time = time.time()
        while th.alive:
            if (timeout is not None) and (time.time() - start_time >= timeout):
                break
        return
    th._alive_lock.acquire()
    th._alive_lock.release()


def open(tid):
    sys.audit(f"{__ROOT__}.thread.open", tid)
    if tid in tstate._threads:
        return tstate._threads[tid]
    state = tstate.ThreadState.__new__(tstate.ThreadState)
    state._id, state._handle = ctypes_defs.open_thread(tid)
    state.__init__()
    state._alive_func = lambda: ctypes_defs.wait_thread(state._id, state._handle, timeout=0)
    return state


