import threading

from .._refs import *


class ThreadError(RuntimeError):
    def __init__(self, *args, state=-1):
        self._state = state
        super().__init__(*args)

    state = property(lambda self: self._state)


class Thread(metaclass=MultiMeta):
    """
    Threading class.

    Represents a base from which you can release as many thread execution
    locks as needed.

    Thread states::
    - 0: the state of a thread base on creation
    - 1: thread is executing, the lock can be joined
    - 2: thread execution has finished, the thread lock is in an unusable state
    """
    def __init__(self, main=None):
        """
        Create a new thread base of state 0.
        """
        if main is None:
            main = self.main
        self._thread_locked = False
        self._running = False
        self._curthread = threading.Thread()
        self._target = main
        self._last_result = None

    def main(self, *args, **kwargs):
        """
        What the thread will do during its lifetime.
        You may override this or pass a callable as parameter
        to __init__()
        """
        pass

    def _wrap_main(self, *args, **kwargs):
        """
        **internal**
        A wrapper around the thread's main.
        """
        self._running = True
        self._last_result = self.main(*args, **kwargs)
        self._running = False

    def start(self, *args, **kwargs):
        """
        Start the thread and begin its lifetime.
        Return the thread execution lock in state 1 that can then be independently manipulated.

        Requires thread state of 0.
        """
        if not self._thread_locked:
            thread = self
            thread._curthread = threading.Thread(target=self._target, args=args, kwargs=kwargs)
            thread._thread_locked = True
            thread._curthread.start()
            return thread
        raise ThreadError(f"Invalid thread state (got {self.state} instead of 0)", state=self.state)

    def join(self, timeout=None):
        """
        Wait until execution finishes, and return its result (return value).
        Current thread execution lock is then in the unusable state of 2.
        Requires thread state of 1.
        """
        if self._running:
            self._curthread.join(timeout=timeout)
            return self._last_result
        raise ThreadError(f"Invalid thread state (got {self.state} instead of 1)", state=self.state)

    def __call__(self, *args, **kwargs):
        """
        Calling self() does the same as start()
        """
        if not self._thread_locked:
            return self.start(*args, **kwargs)
        raise ThreadError(f"Invalid thread state (got {self.state} instead of 0)", state=self.state)

    result = property(lambda self: self._last_result)
    state = property(lambda self: 0 if not self._thread_locked else 1 if self._running else 2)

