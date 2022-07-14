import _thread
import time

from .._meta import MultiMeta
from .._const import *
from .._errors import *
from .._typing import *
from .._local import *


_Lock = _thread.LockType


_main_lock = _thread.allocate_lock()
_main_lock.acquire()


__api = _thread
__blocking_threads = {}
__all_threads = {}


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


# helpers for communicating with other processes:
def _send_distant(wfunc, data):
    """
    Send an order through a pipe to a distant process.
    """
    header = len(data)
    wfunc(header.to_bytes(4, "big", signed=False))
    wfunc(data)


def _receive_distant(rfunc):
    header = int.from_bytes(rfunc(4), "big", signed=False)
    data = rfunc(header)
    if data is None:
        return b""
    return data


def _spec_prop(name, default=None, raise_=False):
    """
    internal helper for properties that depend on whether the thread is in another process or not.
    """
    simple_name = name.removeprefix('__').removesuffix('__')
    return (lambda self: self._get_info(simple_name, default=default, raise_=raise_),
            lambda self, value: self._set_info(simple_name, value))

def _distant_exc_info(wfunc, rfunc):
    _send_distant(wfunc, bytes(ASK_LAST_ERR, encoding=DEFAULT_ENCODING))
    res = _receive_distant(rfunc)
    if res == NULL_BYTE:
        return None, None, None
    info = eval(str(res, encoding=DEFAULT_ENCODING))
    return info[0], info[0](*eval(info[1])), None


@noPath
@customName("main()")
def _run_main_thread(th):
    """
    Run the main program.
    This function's purpose is only to fill in the main thread's '__callable__' slot.
    """
    import __main__
    main_file = open(__main__.__file__, "r+")
    main_code = main_file.read()
    main_file.close()

    local_sys = sys
    local_sys.modules['sys'] = local_sys

    exec(compile(main_code, __main__.__file__, "exec"), {'sys': local_sys}, {})


@customPath(GLOBAL_NAME)
class _RemoteExecution:
    """
    Helper class for running invoked functions
    """
    __qualname__ = "execution_info"

    def __init__(self, function, globals_, *args, **kwargs):
        self.__func__ = function
        self.__args__ = args
        self.__kwargs__ = kwargs
        self.__globals__ = globals_
        self.__result__ = NULL

    def execute(self, thread):
        exec("self.__result__ = self.__func__(th, *self.__args__, **self.__kwargs__)", self.__globals__, {'self': self, 'th': thread})

    result = property(lambda self: self.__result__)

    def __repr__(self):
        return f"<execution info of '{self.__func__}' at {hex(id(self))}>"


# noinspection PyPropertyAccess,PyUnresolvedReferences
class Thread(metaclass=MultiMeta):
    # attributes that may request distant access:
    __tstate__ = property(*_spec_prop('__tstate__', raise_=True))
    __callable__ = property(*_spec_prop('__callable__', default=NO_OP_THREAD_TARGET))
    __join_lock__ = property(*_spec_prop('__join_lock__'))
    __daemon__ = property(*_spec_prop('__daemon__', raise_=True))

    @property
    def __result__(self):
        if self.__tstate__ == STATE_TERMINATED:
            return self._get_info('result')
        raise ThreadStateError("Thread has not finished executing.")

    __result__.setter(_spec_prop('__result__')[1])

    def __init__(self, activity, daemon=False):
        """
        Initialize a new thread model, given what should its threads do as 'activity'.
        'activity' must be a callable that accepts at least one argument, the actual thread.
        """
        self._do_listen = True
        if not callable(activity):
            raise TypeError(TYPE_ERR_STR.format('(Thread, ...) -> Any', type(activity).__name__))
        # noinspection PyUnresolvedReferences
        if hasattr(activity, '__code__') and activity.__code__.co_argcount <= 0:
            raise TypeError(TYPE_ERR_STR.format('(Thread, ...) -> Any', type(activity).__name__))

        self._reach = {"distant": False, "read": None, "write": None}
        self._id = 0  # note that _id is not needed since we aren't distant and create a new local thread.
        self._main = False
        self._exc_info = (None, None, None)
        self._is_tracing_opcode = False
        self._running = False
        self._tracefunc = NO_OP_TRACER
        self._invoke_list = []

        # set our info ourselves since we are local:
        self._set_info('tstate', STATE_INITIALIZED)
        self._set_info('callable', activity)
        self._set_info('join_lock', _thread.allocate_lock())
        self._set_info('daemon', daemon)
        self._set_info('result', None)

        # function standards:
        self.__code__ = activity.__code__ if hasattr(activity, '__code__') else NULL_CODE
        self.__kwdefaults__ = activity.__kwdefaults__ if hasattr(activity, '__kwdefaults__') else None
        self.__defaults__ = activity.__defaults__ if hasattr(activity, '__defaults__') else ()
        self.__annotations__ = activity.__annotations__ if hasattr(activity, '__annotations__') else {}
        self.__builtins__ = activity.__builtins__ if hasattr(activity, '__builtins__') else BUILTINS_DICT
        self.__closure__ = activity.__closure__ if hasattr(activity, '__closure__') else None
        self.__globals__ = activity.__globals__ if hasattr(activity, '__globals__') else globals()
        self.__module__ = activity.__module__ if hasattr(activity, '__module__') else "<unknown>"
        self.__name__ = activity.__name__ if hasattr(activity, '__name__') else f"thread:{self._id}"
        self.__qualname__ = activity.__qualname__ if hasattr(activity, '__qualname__') else \
            f"{self.__module__}.{self.__name__}"

    # noinspection PyDefaultArgument
    @classmethod
    def __obtain__(
            cls,
            id_=None,
            tstate=STATE_INITIALIZED,
            callable_=None,
            lock=None,
            daemon=False,
            is_main=False,
            distance={"distant": False, "read": NO_OP_READER, "write": NO_OP_WRITER},
    ):
        """
        Internal helper for creating a Thread object from an existing thread.
        """
        type_check((id_, tstate, lock, daemon, is_main, distance),
                   (int, None), int, (_thread.LockType, None), bool, bool, dict)

        if 'distant' not in distance:
            distance['distant'] = False
        if 'read' not in distance:
            if distance['distant']:
                raise ValueError("Distant threads must have reading and writing functions.")
            distance['read'] = NO_OP_READER
        if 'write' not in distance:
            if distance['distant']:
                raise ValueError("Distant threads must have reading and writing functions.")
            distance['write'] = NO_OP_WRITER

        if (id_ is None) and distance['distant']:
            raise ValueError("Distant threads must specify and id.")

        if distance['distant']:  # distant threads do not depend on our interpreter instance
            daemon = True

        thread = cls.__new__(cls)
        thread._main = is_main
        thread._reach = distance  # needed for _get_info() and friends
        thread._id = id_ if id_ is not None else 0  # needed for _get_info() and friends since we may be distant
        thread._is_tracing_opcode = False
        thread._do_listen = True
        thread._tracefunc = NO_OP_TRACER
        thread._invoke_list = []

        if thread._main:
            thread._exc_info = (None, None, None)
            lock = _main_lock
            thread._set_info('trace', sys.gettrace())
            sys.settrace(thread._invoker)
        else:
            thread._exc_info = None  # None means we don't support Thread.exc_info()
            thread._set_info('trace', NO_OP_TRACER)


        if callable_ is None:
            if thread._main:
                callable_ = _run_main_thread
            else:
                callable_ = NO_OP_THREAD_TARGET

        if tstate == STATE_INITIALIZED:
            thread._running = False

        if not thread._has_info('daemon'):
            thread._set_info('daemon', daemon)
        if not thread._has_info('callable'):
            thread._set_info('callable', callable_)
        if not thread._has_info('join_lock'):
            thread._set_info('join_lock', lock)
        if not thread._has_info('tstate'):
            thread._set_info('tstate', tstate)

        # function standards:
        thread.__code__ = NULL_CODE
        thread.__kwdefaults__ = {}
        thread.__defaults__ = ()
        thread.__annotations__ = {}
        thread.__builtins__ = BUILTINS_DICT
        thread.__closure__ = None
        thread.__globals__ = globals()
        thread.__module__ = "<unknown>"
        thread.__name__ = f"thread:{thread._id}"
        thread.__qualname__ = f"{thread.__module__}.{thread.__name__}"

        return thread

    def __call__(self, *args, **kwargs):
        """
        Run a model's activity in a separate thread of control given args and kwargs, and return the latter.
        """
        if self.__tstate__ != STATE_INITIALIZED:
            raise ThreadStateError(expected=STATE_INITIALIZED, got=self.__tstate__)
        # here
        if self.__join_lock__ is None:
            raise PermissionError("Access denied.")

        if self._reach['distant']:
            return self._run_distant(*args, **kwargs)

        return self._run_local(*args, **kwargs)

    def __repr__(self):
        if self.__tstate__ == STATE_INITIALIZED:
            return f"<thread model at {hex(id(self))}>"
        return f"<thread {self._id} at {hex(id(self))}, state={_interpret_tstate(self.__tstate__)}>"

    def join(self):
        if self._id == _thread.get_ident():
            raise ThreadStateError("Threads cannot join themselves.")
        if not self._reach['distant']:
            self.__join_lock__.acquire()
            self.__join_lock__.release()
            return
        while self.__tstate__ != STATE_TERMINATED:
            time.sleep(0.5)
        return

    def invoke(self, function, *args, **kwargs):
        if not callable(function):
            raise TypeError(TYPE_ERR_STR.format('(FrameType, str, Any) -> function', type(function).__name__))

        invoked = _RemoteExecution(function, globals(), *args, **kwargs)
        self._invoke_list.append(invoked)
        return invoked

    def settrace(self, function):
        if not callable(function):
            raise TypeError(TYPE_ERR_STR.format('(FrameType, str, Any) -> function', type(function).__name__))
        # noinspection PyUnresolvedReferences
        if hasattr(function, '__code__') and function.__code__.co_argcount != 3:
            raise TypeError(TYPE_ERR_STR.format('(FrameType, str, Any) -> function', type(function).__name__))

        if self.__tstate__ == STATE_TERMINATED:
            return

        self._tracefunc = function

    def gettrace(self):
        if self._tracefunc == NO_OP_TRACER:
            return None
        return self._tracefunc

    def exc_info(self):
        if self.__tstate__ != STATE_INITIALIZED:
            return self._exc_info

    @staticmethod
    def get_main():
        return _main_thread

    def __stop_listener__(self):
        self._do_listen = False

    def _run_distant(self, *args, **kwargs):
        _send_distant(self._reach['write'], bytes(THREAD_EXECUTE, encoding=DEFAULT_ENCODING))
        _res = _receive_distant(self._reach['read'])
        if _res == TPM_ERR_PERMISSION:  # something went wrong when calling the thread
            raise PermissionError("Access denied.")
        elif _res == NULL_BYTE:
            exc_info = _distant_exc_info(self._reach['write'], self._reach['read'])
            res = MultiMeta.copy(self)
            res.__tstate__ = STATE_TERMINATED
            res._exc_info = exc_info
            return res

        new_id = int.from_bytes(_res, "big", signed=False)
        res: Thread = MultiMeta.copy(self)
        res._id = new_id
        res._running = True
        return res

    def _run_local(self, *args, **kwargs):
        res: Thread = MultiMeta.copy(self)

        def activity():
            res.__join_lock__.acquire()

            time.sleep(0.01)
            exc_info = res._exc_info if res._exc_info is not None else (None, None, None)
            sys.settrace(self._invoker)

            try:
                result = res.__callable__(res, *args, **kwargs)
                res._set_info('result', result)
            except:
                exc_info = sys.exc_info()
                sys.stderr.write(f"Exception ignored in thread {res._id}:\n")
                sys.excepthook(*sys.exc_info())

            res._exc_info = exc_info
            res.__tstate__ = STATE_TERMINATED
            res._running = False
            res._unrecord()
            res.__join_lock__.release()

        res.__tstate__ = STATE_RUNNING
        res._id = _thread.start_new_thread(activity, ())
        res._running = True
        res._record()
        time.sleep(0.03)
        return res

    def _record(self):
        if not self.__daemon__:
            globals()['__blocking_threads'][self._id] = self
        globals()['__all_threads'][self._id] = self

    def _unrecord(self):
        if not self.__daemon__:
            del globals()['__blocking_threads'][self._id]
        del globals()['__all_threads'][self._id]

    def _invoker(self, frame, event, args):
        if self._reach['distant'] and (len(self._invoke_list) > 0):
            raise NotImplementedError("Cannot invoke a callable in a distant process.")

        self._tracefunc(frame, event, args)
        if not self._is_tracing_opcode:
            frame.f_trace_opcodes = True
            self._is_tracing_opcode = True

        if event == EVENT_OPCODE:
            if len(self._invoke_list) > 0:
                invoked = self._invoke_list[0]
                try:
                    invoked.execute(self)
                except:
                    sys.stderr.write(f"Exception ignored for remote call in thread {self._id}:\n")
                    sys.excepthook(*sys.exc_info())
                self._invoke_list.pop(0)

        return self._invoker


    def _get_info(self, key, default=None, raise_=False):
        result = NULL_BYTE
        if self._reach['distant'] and self._running:
            msg = GET_THREAD_ATTR.format(self._id, key)
            _send_distant(self._reach['write'], bytes(msg, encoding=DEFAULT_ENCODING))
            res = _receive_distant(self._reach['read'])
            if res != NULL_BYTE:
                result = eval(res)
        else:
            try:
                result = getattr(self, f"#{key}")
            except AttributeError:
                pass

        if result == NULL_BYTE:
            if raise_:
                raise AttributeError(ATTRIB_ERR_STR.format(type(self).__name__, key))
            return default
        return result

    def _set_info(self, key, value):
        if self._reach['distant'] and self._running:
            real_value = repr(value) if eval(repr(value)) == value else eval(value.__dict__)
            msg = SET_THREAD_ATTR.format(self._id, key, real_value)
            _send_distant(self._reach['write'], bytes(msg, encoding=DEFAULT_ENCODING))
            success = int.from_bytes(_receive_distant(self._reach['read']), "big")
            if success < 0:
                raise AttributeError("Readonly attribute.")
            return

        setattr(self, f"#{key}", value)

    def _has_info(self, name):
        try:
            self._get_info(name, raise_=True)
        except AttributeError:
            return False
        return True

    def _get_result(self):
        if self.__tstate__ == STATE_TERMINATED:
            return self._get_info('result')
        raise ThreadStateError("Thread has not finished executing.")


    state = property(lambda self: _interpret_tstate(self.__tstate__))
    id = property(lambda self: self._id)
    daemon = property(lambda self: self.__daemon__)
    result = property(lambda self: self.__result__)


_main_thread = Thread.__obtain__(
    id_=MAIN_THREAD_ID, tstate=STATE_RUNNING, callable_=_run_main_thread, is_main=True, lock=_main_lock,
    distance={'distant': False, 'read': None, 'write': None}
)


def __finalize__():
    blocking = __blocking_threads.copy()
    for _id, _thread in blocking.items():
        _thread.join()
        _thread.__stop_listener__()
    try:
        _main_lock.release()
    except:
        pass


