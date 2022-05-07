import _thread
import sys
import time

from .._const import *
from .._errors import *
from .._typing import *

from .._meta import MultiMeta as _Mt


__api = _thread
__blocking_threads = {}
__all_threads = {}

_main_lock = _thread.allocate_lock()
_main_lock.acquire()


def _interpret_tstate(tstate):
    match tstate:
        case 0:
            return "Initialized"
        case 1:
            return "Running"
        case 2:
            return "Finalized"
        case _:
            return f"<thread state {tstate}>"


class _RemoteExecutor:
    def __init__(self, function, globals_, *args, **kwargs):
        self.__func__ = function
        self.__args__ = args
        self.__kwargs__ = kwargs
        self.__globals__ = globals_

    def execute(self, thread):
        exec("self.__func__(th, *self.__args__, **self.__kwargs__)", self.__globals__, {'self': self, 'th': thread})


class Thread(metaclass=_Mt):
    """
    Class representing threads.
    When instantiated, this class returns a thread model that can only be called.
    When called, thread models pass given arguments to the function representing its activity upon
    calling it into a separate thread of control. A Thread object representing the actual thread
    of control in a running state is returned.
    """

    def __init__(self, activity, daemon=False):
        """
        Initialize a new thread model, given what should its threads do as 'activity'.
        'activity' must be a callable that accepts at least one argument, the actual thread.
        """
        if not callable(activity):
            raise TypeError(TYPE_ERR_STR.format('(Thread, ...) -> Any', type(activity).__name__))
        if hasattr(activity, '__code__') and activity.__code__.co_argcount <= 0:
            raise TypeError(TYPE_ERR_STR.format('(Thread, ...) -> Any', type(activity).__name__))

        self.__tstate__ = TSTATE_INITIALIZED
        self.__callable__ = activity
        self.__join_lock__ = _thread.allocate_lock()
        self.__daemon__ = daemon
        self.__remote_executions__ = []
        self.__trace__ = lambda frame, event, args: None
        self._result = None
        self.__id__ = 0
        self.__exc_info__ = (None, None, None)
        self._is_tracing_opcode = False
        self._main = False
        self._accessor = None

        # function standards:
        self.__code__ = activity.__code__ if hasattr(activity, '__code__') else NULL_CODE

    def __call__(self, *args, **kwargs):
        """
        Run a model's activity in a separate thread of control given args and kwargs, and return the latter.
        """
        if self.__tstate__ != TSTATE_INITIALIZED:
            raise ThreadStateError(expected=TSTATE_INITIALIZED, got=self.__tstate__)
        res: Thread = _Mt.copy(self)

        def activity():
            res.__join_lock__.acquire()
            time.sleep(0.01)
            exc_info = res.exc_info()

            sys.settrace(res._trace_opcodes)
            try:
                res._result = res.__callable__(res, *args, **kwargs)
            except:
                exc_info = sys.exc_info()
                sys.stderr.write(f"Exception ignored in thread {res.__id__}:\n")
                sys.excepthook(*sys.exc_info())
            res.__join_lock__.release()
            res.__tstate__ = TSTATE_FINALIZED
            res.__exc_info__ = exc_info
            res._release()

        res.__tstate__ = TSTATE_RUNNING
        res.__id__ = _thread.start_new_thread(activity, ())
        time.sleep(0.03)

        if not res.__daemon__:
            globals()['__blocking_threads'][res.__id__] = res

        globals()['__all_threads'][res.__id__] = res
        return res

    @classmethod
    def __from_attrs__(
            cls, tstate=TSTATE_INITIALIZED,
            callable_=lambda th, *args, **kwargs: None,
            lock=_thread.allocate_lock(),
            daemon=False,
            id_=_thread.get_ident(),
            is_main=False,
            sendfunc=lambda msg: None,
            recvfunc=lambda size: None,
    ):
        thread = cls.__new__(cls)
        thread.__tstate__ = tstate
        thread.__callable__ = callable_
        thread.__join_lock__ = lock
        thread.__daemon__ = daemon
        thread.__id__ = id_
        thread._main = is_main
        thread._accessor = None
        if not is_main and lock is None:
            thread._accessor = (sendfunc, recvfunc)
        return thread

    def _send_distant(self, data):
        """
        Send an order through a pipe to a distant process.
        """
        if self._accessor is None:
            raise ProcessLookupError("Couldn't lookup thread's owner process.")
        sendfunc = self._accessor[1]
        header = len(data)
        sendfunc(header.to_bytes(4, "big", signed=False))
        sendfunc(data)

    def _receive_distant(self, size):
        if self._accessor is None:
            raise ProcessLookupError("Couldn't lookup thread's owner process.")
        recvfunc = self._accessor[0]
        header = int.from_bytes(recvfunc(4), "big", signed=False)
        data = recvfunc(header)
        if data is None:
            return b""
        return data

    def _trace_opcodes(self, frame, event, args):
        """
        Internal function for executing operations just before an opcode is executed.
        """
        self.__trace__(frame, event, args)
        if not self._is_tracing_opcode:
            frame.f_trace_opcodes = True
            self._is_tracing_opcode = True

        if event == EVENT_OPCODE:
            if len(self.__remote_executions__) > 0:
                executor = self.__remote_executions__[0]
                try:
                    executor.execute(self)
                except:
                    sys.stderr.write(f"Exception ignored for remote call in thread {self.__id__}:\n")
                    sys.excepthook(*sys.exc_info())
                self.__remote_executions__.pop(0)

        return self._trace_opcodes

    def _release(self):
        del globals()['__all_threads'][self.__id__]

    def invoke(self, function, *args, **kwargs):
        """
        Invoke the specified callable into the thread.
        The callable will then wait to be executed between other actions of the thread.
        Upon execution, it will be passed in the actual thread object as first parameter, and given
        globals() at the moment of the call to Thread.invoke() as globals for execution.
        Return value is ignored.
        If the thread has already finished executing, ThreadStateError is raised.

        Keep in mind that this will block the thread until the function returns.
        """
        if self.__tstate__ in (TSTATE_INITIALIZED, TSTATE_FINALIZED):
            raise ThreadStateError("Thread must be running to invoke calls.")
        if not callable(function):
            raise TypeError(TYPE_ERR_STR.format('(Thread, ...) -> Any', type(function).__name__))
        if hasattr(function, '__code__') and function.__code__.co_argcount <= 0:
            raise TypeError(TYPE_ERR_STR.format('(Thread, ...) -> Any', type(function).__name__))

        executor = _RemoteExecutor(function, globals(), *args, **kwargs)
        self.__remote_executions__.append(executor)

        # disallow more than 63 functions to wait for execution at a time:
        if len(self.__remote_executions__) >= 64:
            raise OverflowError("Too much objects are waiting to be called.")

    def settrace(self, function):
        """
        Set the tracing function for this thread.
        Do not use sys.settrace() on threads, otherwise their invoke() functionality
        could break. Use this function instead.
        """
        if self.__tstate__ == TSTATE_FINALIZED:
            return
        if not callable(function):
            raise TypeError(TYPE_ERR_STR.format('(FrameType, str, Any) -> None', type(function).__name__))
        if hasattr(function, '__code__') and function.__code__.co_argcount != 3:
            raise TypeError(TYPE_ERR_STR.format('(FrameType, str, Any) -> None', type(function).__name__))

        self.__trace__ = function

    def join(self):
        """
        Wait until the given thread of control has finished executing.
        A thread of control that has finished executing is in an unusable state. The only data
        you can get from it are Thread.exc_info() and the return value of the thread's activity.
        """
        if self.__id__ == _thread.get_ident():
            raise ThreadStateError("Threads cannot join themselves.")
        if self.__join_lock__ is None:  # this happens for the main thread
            if self._main:
                _main_lock.acquire()
                _main_lock.release()
            else:
                raise OutOfScopeError("Can only join threads owned by this process.")
        if self.__tstate__ == TSTATE_FINALIZED:
            return
        if self.__tstate__ != TSTATE_RUNNING:
            raise ThreadStateError(expected=TSTATE_RUNNING, got=self.__tstate__)
        self.__join_lock__.acquire()
        self.__join_lock__.release()

    @staticmethod
    def get_main():
        """
        Return the main thread of control of this program.
        Usually, it is the thread from which the Python interpreter was started.
        """
        _main_thread._result = None
        return _main_thread

    def exc_info(self):
        """
        Return the last exception caught in the current thread of control.
        Return None if the thread has not been executed or is a thread model.
        """
        if self.__tstate__ == TSTATE_INITIALIZED:
            return None
        return self.__exc_info__

    @property
    def result(self):
        if self.__tstate__ != TSTATE_FINALIZED:
            raise ThreadStateError("Thread has not returned yet.")
        return self._result

    @property
    def state(self):
        """
        The current state of this thread.
        """
        return _interpret_tstate(self.__tstate__)

    @property
    def id(self):
        """
        Unique identifier for this thread of control.
        Thread models do not have ids since they are not running.
        """
        if self.__tstate__ == TSTATE_INITIALIZED:
            raise ThreadStateError("Thread models do not have ids.")
        return self.__id__

    @property
    def daemon(self):
        """
        Whether this thread is daemon or not.
        Daemon threads will not be waited for by the interpreter before exiting.
        """
        return self.__daemon__

    def __repr__(self):
        if self.__tstate__ == TSTATE_INITIALIZED:
            return f"<thread model at {hex(id(self))}>"
        return f"<thread {self.__id__} at {hex(id(self))}, state={_interpret_tstate(self.__tstate__)}>"


# set the main thread variable for it to be available for Thread.get_main():
_main_thread = Thread.__from_attrs__(
    tstate=TSTATE_RUNNING,
    lock=None,
    is_main=True
)

def __finalize__():  # submodule finalizer (callback)
    """
    Wait until all non-daemon threads are finished before exiting the interpreter.
    """
    for _id, _thread in __blocking_threads.items():
        _thread.join()
    _main_lock.release()

