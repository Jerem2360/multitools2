import _thread
import sys
import threading
from itertools import count

from . import runtime


class _ThreadSafe_dict(dict):
    """
    A thread-safe version of dict.
    Access is governed by a lock to avoid race conditions.
    """
    def __init__(self, source={}):
        super().__init__(source)
        self._lock = _thread.allocate_lock()

    def __getitem__(self, item):
        with self._lock:
            return super().__getitem__(item)

    def __setitem__(self, key, value):
        # print('setting', key, '=', value)
        with self._lock:
            return super().__setitem__(key, value)

    def __delitem__(self, key):
        with self._lock:
            return super().__delitem__(key)


class _MyLock:
    """
    A lock that allows to know which thread currently owns it.
    """

    def __init__(self):
        self._lock = _thread.allocate_lock()
        self._do_unlock = True
        self._owner = 0
        self._owner_lock = _thread.allocate_lock()

    def __enter__(self):
        if self.owned:
            self._do_unlock = False
            return self
        self.acquire()
        self._do_unlock = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._do_unlock:
            self.release()

    def acquire(self, blocking=True, timeout=-1):
        result = self._lock.acquire(blocking=blocking, timeout=timeout)
        if result:
            with self._owner_lock:
                self._owner = _thread.get_native_id()
        return result

    def release(self):
        self._lock.release()
        with self._owner_lock:
            self._owner = 0

    @property
    def owner(self):
        """
        The thread that currently owns the lock.
        """
        with self._owner_lock:
            if not self._owner:
                return None
            return _threads[self._owner]

    @property
    def owned(self):
        """
        Whether the current thread already owns the lock.
        Security measure to avoid deadlock.
        """
        with self._owner_lock:
            return self._owner == _thread.get_native_id()

    @property
    def locked(self):
        """
        Whether the thread is locked.
        """
        return self._lock.locked()

    def __del__(self):
        if self.owned:
            self.release()


_threads = _ThreadSafe_dict()  # threads owned by the current process


class ThreadState:
    """
    The current state of a thread.

    id: unique identifier for the thread.

    exc_info: exception information of the thread.

    call_stack: the call stack of the thread.

    alive: if the thread is alive.
    """

    def __init__(self, thread_obj=None):
        tid = _thread.get_native_id()
        if not hasattr(self, '_id'):
            self._id = tid

        # print('id:', self._id)
        self._thread = thread_obj
        self._lock = _MyLock()  # we would have risked deadlock
        self._alive_lock = _MyLock()  # will be None for non-python threads.
        self._stack = runtime.Stack(self._stack_getitem, self._stack_len)
        self._stack.__name__ = f"t{hex(self._id)}:call_stack"
        self._alive_func = None
        self._alive_args = ()
        if not hasattr(self, '_handle'):
            self._handle = None
        _threads[self._id] = self

    def _begin(self):
        """
        Called to initialize the state of the thread.
        """
        if not self._alive_lock.owned:
            return self._alive_lock.acquire(blocking=False)
        return False

    def _end(self):
        """
        Called to finalize the state of the thread.
        """
        if self._alive_lock.owned:
            self._alive_lock.release()
        del _threads[self._id]

    def _getframe(self, depth):
        if _thread.get_native_id() == self._id:
            depth += 1
        f = sys._current_frames()[self._id]
        depth = -depth
        while depth:
            # print(depth)
            f = f.f_back
            if f is None:
                raise ValueError
            depth += 1
        return f

    def _stack_getitem(self, stack, depth):
        if self._id not in sys._current_frames():
            from .errors import configure
            raise IndexError("Index out of range.") from configure(trace_depth=2)
        if _thread.get_native_id() == self._id:
            depth += 2
        caller_size = len(stack)
        if depth < 0:
            depth = caller_size + depth
        try:
            return self._getframe(depth)
        except ValueError:
            from .errors import configure
            raise IndexError("Index out of range.") from configure(trace_depth=2)

    def _stack_len(self, stack):
        if self._id not in sys._current_frames():
            return 0
        size_hint = 1
        frame = None
        try:
            while True:
                frame = self._getframe(size_hint)
                size_hint *= 2
        except ValueError:
            if frame:
                size_hint //= 2
            else:
                while not frame:
                    size_hint = max(2, size_hint // 2)
                    try:
                        frame = self._getframe(size_hint)
                    except ValueError:
                        continue

        for size in count(size_hint):
            frame = frame.f_back
            if not frame:
                if _thread.get_native_id() == self._id:
                    return size - 1
                return size

    @property
    def id(self):
        """
        Identifier for the thread.
        """
        with self._lock:
            return self._id

    @property
    def exc_info(self):
        """
        Exception information about the thread.
        Can be None if unavailable.
        """
        with self._lock:
            if self._id not in sys._current_exceptions():
                return None
            return sys._current_exceptions()[self._id]

    @property
    def call_stack(self):
        """
        The thread's call stack.
        Can be empty.
        """
        with self._lock:
            return self._stack

    @property
    def alive(self):
        """
        Whether the thread is alive.
        """
        if self._alive_lock is None:
            return self._alive_func(*self._alive_args)
        return self._alive_lock.locked


# print("this is main:")
main_thread = ThreadState()
"""The state of the main thread of the current process."""

# of course the main thread is alive.
_l = main_thread._alive_lock.acquire(blocking=False)

if not _l:
    raise OSError("Failed to acquire the main thread's lock.")

del _l


def _register_thread(ident):
    _th = ThreadState.__new__(ThreadState)
    _th._id = ident
    _th.__init__()
    return _th


# threads created previously from the threading module must be registered:
for th in threading.enumerate():
    if th.native_id not in _threads:  # do not register twice the same thread
        _th = _register_thread(th.native_id)
        _th._alive_func = lambda: th.is_alive()

