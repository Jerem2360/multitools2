import os
import types as _types
import _thread
import time

from .._meta import MultiMeta
from .._const import *
from .._typing import *
from .._errors import *
from .._helpers import *


_blocking_threads = {}
"""
Thread:
- Thread(target=lambda th, *args, **kwargs: None, daemon=False)
- join()
- __call__(*args, **kwargs)
- invoke(function, *args, **kwargs)
- __getstate__()
- __setstate__()
- exc_info()
- tid
- owner_proc
- daemon
- settrace()
- gettrace()
"""


class _ExecutionFrame:
    def __init__(self, function, args, kwargs):
        self.data = function, args, kwargs

    def execute(self):
        self.result = self.data[0](*self.data[1], **self.data[2])


class Thread(metaclass=MultiMeta):
    """
    Class representing a Thread.
    Same three states as for the Process class.

    **Do not use standard sys.settrace() and sys.gettrace() functions inside threads,
    since they could alter and most of the time break the invoking and exc_info() functionalities.**

    On the other hand, standard sys.exc_info() should work properly inside threads.

    Threads have their standard outputs and input (sys.stdin, sys.stdout and sys.stderr) bound to that
    of their owner process.
    In consequence, threads owned by the main process have their standard outputs and input
    bound to the main python console.
    """
    def __new__(cls, *args, **kwargs):
        """
        Create and return a new Thread object.
        """
        from . import _process   # avoid circular import

        __mcs = metaclassof(cls)
        if __mcs != MultiMeta:
            raise TypeError("Thread.__new__() was passed an object of an invalid type as 'self'.") from None

        self = super().__new__(cls)

        __mcs.set_info(self, 'needs_init', True)
        match len(args):
            case 2:  # special case where we need to open an existing thread
                owner, tid = args
                type_check((owner, tid), _process.Process, int)

                __mcs.set_info(self, 'owner_proc', owner)
                __mcs.set_info(self, 'id', tid)
                __mcs.set_info(self, 'state', STATE_RUNNING)
                __mcs.set_info(self, 'needs_init', False)

                __mcs.set_info(self, 'target', NO_OP_THREAD_TARGET)
                __mcs.set_info(self, 'daemon', True)
                __mcs.set_info(self, 'trace', NO_OP_TRACER)
                __mcs.set_info(self, 'invoke_list', [])
                __mcs.set_info(self, 'lock', _thread.allocate_lock())
                __mcs.set_info(self, 'is_being_called', False)
                __mcs.set_info(self, 'exc_info', (None, None, None))

            case _:
                pass

        return self

    def __init__(self, *args, **kwargs):
        """
        Initialize a Thread object.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Thread.__init__() was passed an object of an invalid type as 'self'.") from None

        if not __mcs.get_info(self, 'needs_init'):
            return
        __mcs.set_info(self, 'needs_init', False)

        daemon = kwargs.get('daemon', False)

        match len(args):
            case 0:
                target = NO_OP_THREAD_TARGET
            case 1:
                target = args[0]
                type_check((target,), _types.FunctionType)

            case _:
                raise TypeError(POS_ARGCOUNT_ERR_STR.format('Thread.__init__()', '0 or 1', len(args)))

        __mcs.set_info(self, 'owner_proc', None)
        __mcs.set_info(self, 'target', target)
        __mcs.set_info(self, 'daemon', daemon)
        __mcs.set_info(self, 'id', 0)
        __mcs.set_info(self, 'state', STATE_INITIALIZED)
        __mcs.set_info(self, 'trace', NO_OP_TRACER)
        __mcs.set_info(self, 'invoke_list', [])
        __mcs.set_info(self, 'lock', _thread.allocate_lock())
        __mcs.set_info(self, 'is_being_called', False)
        __mcs.set_info(self, 'exc_info', (None, None, None))

    def _invoker(self, frame, event, args):
        """
        Internal callback that will call invoked functions inside the said thread.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Thread._invoker() was passed an object of an invalid type as 'self'.") from None
        tracefunc = __mcs.get_info(self, 'trace')
        tracefunc(frame, event, args)

        if not frame.f_trace_opcodes:
            frame.f_trace_opcodes = True

        if event == EVENT_OPCODE:
            invoke_list = __mcs.get_info(self, 'invoke_list')
            if len(invoke_list) > 0:
                invoked = invoke_list[0]
                try:
                    invoked.execute()
                except:
                    sys.stderr.write(f"Exception ignored for invoke in thread {__mcs.get_info(self, 'id')}:\n")
                    sys.excepthook(*sys.exc_info())
                invoke_list.pop(0)
                __mcs.set_info(self, 'invoke_list', invoke_list)


        if sys.exc_info() != __mcs.get_info(self, 'exc_info'):
            __mcs.set_info(self, 'exc_info', sys.exc_info())

        return self._invoker

    def __mul__(self, other):
        match other:
            case 1:
                return self
            case 0:
                return 0
            case _:
                raise TypeError(f"Unsupported operand values {repr(self)}, {repr(other)} for *.") from None

    def __call__(self, *args, **kwargs):
        """
        Call a thread model starting a new thread, and return its thread activity.
        """
        from . import _process
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Thread.__call__() was passed an object of an invalid type as 'self'.") from None

        if __mcs.get_info(self, 'state') != STATE_INITIALIZED:
            raise ThreadStateError("Only thread models can be called.")

        timeout = 5000

        start_time = time.time()
        while __mcs.get_info(self, 'is_being_called') * ((time.time() - start_time) < (timeout / 1000)):
            pass
        if time.time() - start_time > timeout / 1000:
            return  # timeout expired

        __mcs.set_info(self, 'is_being_called', True)

        th = __mcs.copy(self)

        def thread_start(th_args, th_kwargs):
            __mcs.set_info(globals()['th'], 'state', STATE_RUNNING)
            __mcs.set_info(globals()['th'], 'running', True)

            if not __mcs.get_info(globals()['th'], 'daemon'):
                globals()['_blocking_threads'][__mcs.get_info(globals()['th'], 'id')] = globals()['th']

            __mcs.get_info(globals()['th'], 'lock').acquire()
            time.sleep(0.01)
            __mcs.set_info(globals()['th'], 'id', _thread.get_native_id())

            sys.settrace(globals()['th']._invoker)

            target = __mcs.get_info(globals()['th'], 'target')

            try:
                result = target(globals()['th'], *th_args, **th_kwargs)
            except SystemExit:
                pass
            except KeyboardInterrupt:
                pass
            except:
                sys.stderr.write(f"Exception ignored in thread {__mcs.get_info(globals()['th'], 'id')}:\n")
                sys.excepthook(*sys.exc_info())

            counter = 0
            for invokable in __mcs.get_info(globals()['th'], 'invoke_list'):
                if counter >= 20:  # maximum number of trailing functions that can be executed at the end of the thread.
                    break

                print('running trailing invoked function...')
                try:
                    invokable.execute()
                except:
                    sys.stderr.write(f"Exception ignored for invoke in thread {__mcs.get_info(globals()['th'], 'id')}:\n")
                    sys.excepthook(*sys.exc_info())
                counter += 1


            __mcs.set_info(globals()['th'], 'state', STATE_TERMINATED)
            __mcs.set_info(globals()['th'], 'running', False)

            if not __mcs.get_info(globals()['th'], 'daemon'):
                del globals()['_blocking_threads'][__mcs.get_info(globals()['th'], 'id')]

            __mcs.get_info(globals()['th'], 'lock').release()

        owner = _process.Process.get_current_process()
        __mcs.set_info(self, 'owner_proc', owner)
        if owner.pid not in _process._pthreads_info:
            raise ProcessError('Owner process has finished executing.')

        _process._pthreads_info[owner.pid][__mcs.get_info(th, 'id')] = th  # update our record of known threads per process.

        _thread.start_new_thread(thread_start, (args, kwargs), kwargs={})
        time.sleep(0.03)

        __mcs.set_info(th, 'is_being_called', False)
        __mcs.set_info(self, 'is_being_called', False)

        return th

    def __repr__(self):
        """
        Implement repr(self)
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Thread.__repr__() was passed an object of an invalid type as 'self'.") from None

        if __mcs.get_info(self, 'state') == STATE_INITIALIZED:
            model_name = f" at {hex(id(self))}" if __mcs.get_info(self, 'target') == NO_OP_PROCESS_TARGET \
                else f" '{__mcs.get_info(self, 'target').__name__}'"
            return f"<thread model{model_name}>"
        return f"<thread {__mcs.get_info(self, 'id')} at {hex(id(self))}>"

    def __getstate__(self):
        """
        Helper for pickle.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Thread.__getstate__() was passed an object of an invalid type as 'self'.") from None

        return {
            'owner_proc': __mcs.get_info(self, 'owner_proc').pid,
            'id': __mcs.get_info(self, 'id'),
            'state': __mcs.get_info(self, 'state'),
            'daemon': __mcs.get_info(self, 'daemon'),
            'is_being_called': __mcs.get_info(self, 'is_being_called'),
            'exc_info': __mcs.get_info(self, 'exc_info'),
            **pickle_function(__mcs.get_info(self, 'target'), 'target'),
            **pickle_function(__mcs.get_info(self, 'trace'), 'trace')
        }

    def __setstate__(self, state):
        """
        Helper for pickle.
        """
        from . import _process   # avoid circular import

        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Thread.__setstate__() was passed an object of an invalid type as 'self'.") from None

        _target = unpickle_function(state, 'target')
        _trace = unpickle_function(state, 'trace')
        _owner_id = state['owner_proc']
        _id = state['id']
        _state = state['state']
        _daemon = state['daemon']
        _is_being_called = state['is_being_called']
        _exc_info = state['exc_info']

        __mcs.set_info(self, 'target', _target)
        __mcs.set_info(self, 'trace', _trace)
        __mcs.set_info(self, 'owner_proc', _process.Process.__open__(_owner_id))
        __mcs.set_info(self, 'id', _id)
        __mcs.set_info(self, 'state', state)
        __mcs.set_info(self, 'daemon', _daemon)
        __mcs.set_info(self, 'is_being_called', _is_being_called)
        __mcs.set_info(self, 'exc_info', _exc_info)

        # if the thread thinks it's still running:
        if _state == STATE_RUNNING:
            # thread was unpickled after it has finished executing.
            if (_owner_id not in _process._pthreads_info) or (_id not in _process._pthreads_info[_owner_id]):
                __mcs.set_info(self, 'state', STATE_TERMINATED)
                return

            # if it was right, make sure we have recorded it as an active thread:
            _process._pthreads_info[_owner_id][_id] = self  # update our record of known threads per process.

    def invoke(self, function, *args, **kwargs):
        """
        Invoke a function in a thread, given args and kwargs.
        This will tell the thread that it should execute this function with given arguments
        whenever possible, i.e. between two opcodes.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Thread.invoke() was passed an object of an invalid type as 'self'.") from None

        frame = _ExecutionFrame(function, args, kwargs)
        invoke_list = __mcs.get_info(self, 'invoke_list')
        invoke_list.append(frame)
        __mcs.set_info(self, 'invoke_list', invoke_list)

    def exc_info(self):
        """
        Return the error status of the thread, as returned by sys.exc_info().
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Thread.exc_info() was passed an object of an invalid type as 'self'.") from None

        return __mcs.get_info(self, 'exc_info')

    def settrace(self, trace):
        """
        Equivalent of sys.settrace(), but only for this thread activity or model.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Thread.settrace() was passed an object of an invalid type as 'self'.") from None

        __mcs.set_info(self, 'trace', trace)

    def gettrace(self):
        """
        Equivalent of sys.gettrace(), but only for this thread activity or model.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Thread.gettrace() was passed an object of an invalid type as 'self'.") from None
        return __mcs.get_info(self, 'trace')

    def join(self):
        """
        Wait until the thread has finished executing.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Thread.join() was passed an object of an invalid type as 'self'.") from None

        if __mcs.get_info(self, 'id') == _thread.get_native_id():
            raise ThreadStateError('A thread cannot join itself.')

        __mcs.get_info(self, 'lock').acquire(blocking=True)
        __mcs.get_info(self, 'lock').release()

    @staticmethod
    def sleep(ms):
        """
        Wait for 'ms' milliseconds in the current thread.
        """
        type_check((ms,), int)
        time.sleep(ms / 1000)

    @property
    def tid(self):
        """
        The native id of the thread.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("'Thread.tid.fget()' was passed an object of an invalid type as 'self'.") from None

        return __mcs.get_info(self, 'id')

    @property
    def daemon(self):
        """
        Whether this thread is a daemon thread.
        The interpreter always waits for non-daemon threads to finish executing before exiting.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("'Thread.daemon.fget()' was passed an object of an invalid type as 'self'.") from None

        return __mcs.get_info(self, 'daemon')

    @property
    def owner(self):
        """
        The process that owns the thread, i.e. the one it was created from.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("'Thread.owner.fget()' was passed an object of an invalid type as 'self'.") from None
        return __mcs.get_info(self, 'owner_proc')

def __finalize__():
    """
    Wait for all non-daemon threads to finish their execution.
    """
    for thread in _blocking_threads:
        thread.join()

