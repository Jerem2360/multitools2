from .._meta import *
from .._const import *
from .._errors import *
from .._typing import *
from .._helpers import *

from types import FunctionType
import _thread
import sys
import time


def _get_current_process(): ...  # forward declaration, real value is 'lambda: Process.current_process()'


class Thread(metaclass=MultiMeta):
    def __new__(cls, *args, **kwargs):
        daemon = kwargs.get('daemon', False)
        _process = kwargs.get('_process', None)
        _tstate = kwargs.get('_tstate', STATE_INITIALIZED)
        _can_init = kwargs.get('_can_init', True)
        _id = kwargs.get('id', 0)
        target = args[0] if len(args) == 1 else kwargs.get('target', NO_OP_THREAD_TARGET)

        if len(args) > 1:
            raise TypeError(POS_ARGCOUNT_ERR_STR.format('Thread.__new__()', '0 or 1', repr(len(args))))

        _proc_module = sys.modules[f"{MODNAME_PROCESS}._processes"]
        _ProcType = _proc_module.Process

        type_check((daemon, target, _tstate, _can_init, _process), bool, FunctionType, int, bool, _ProcType)

        self = super().__new__()
        self._daemon = daemon
        self._target = target
        self._owner_process = _process
        self._tracefunc = NO_OP_TRACER
        self._can_init = _can_init
        self._tstate = _tstate
        self._id = _id
        self._running = (_tstate != STATE_INITIALIZED)
        self._is_being_called = False

        self.__code__ = target.__code__
        self.__kwdefaults__ = target.__kwdefaults__
        self.__defaults__ = target.__defaults__
        self.__annotations__ = target.__annotations__
        self.__builtins__ = target.__builtins__
        self.__closure__ = target.__closure__
        self.__globals__ = target.__globals__
        self.__module__ = target.__module__
        self.__name__ = target.__name__
        self.__qualname__ = target.__qualname__

        return self

    def __init__(self, *args, **kwargs):
        if not self._can_init:
            return
        self._can_init = False

        self._tstate = STATE_INITIALIZED
        self._id = 0
        self._exc_info = (None, None, None)
        self._is_tracing = False
        self._running = False
        self._invoke_list = []

    def __call__(self, *args, **kwargs):
        while self._is_being_called:
            pass

        self._is_being_called = True
        res = MultiMeta.copy(self)

        # to do start the thread ...

        res._is_being_called = False
        self._is_being_called = False

        return res

    def __getstate__(self):
        return {
            'daemon': self._daemon,
            'proc': self._owner_process.pid,
            'can_init': self._can_init,
            'tstate': self._tstate,
            'id': self._id,
            'exc_info': (self._exc_info[0], self._exc_info[1]) if '_exc_info' in dir(self) else (None, None),
            'is_tracing': self._is_tracing if '_is_tracing' in dir(self) else False,
            'invoke_list': tuple(self._invoke_list) if '_invoke_list' in dir(self) else (),
            'running': self._running,
            'processType': type(self._owner_process),
            **pickle_function(self._target, 'target'),
            **pickle_function(self._tracefunc, 'trace'),
        }

    def __setstate__(self, state):
        self._target = unpickle_function(state, 'target')
        self._tracefunc = unpickle_function(state, 'trace')

        self._owner_process = state['processType'].__open__(state['proc'])
        self._id = state['id']
        self._daemon = state['daemon'] if self._id == _thread.get_native_id() else True
        self._invoke_list = list(state['invoke_list'])
        self._is_tracing = state['is_tracing']
        self._exc_info = (*state['exc_info'], None)
        self._tstate = state['tstate']
        self._running = state['running']

        self.__code__ = self._target.__code__
        self.__kwdefaults__ = self._target.__kwdefaults__
        self.__defaults__ = self._target.__defaults__
        self.__annotations__ = self._target.__annotations__
        self.__builtins__ = self._target.__builtins__
        self.__closure__ = self._target.__closure__
        self.__globals__ = self._target.__globals__
        self.__module__ = self._target.__module__
        self.__name__ = self._target.__name__
        self.__qualname__ = self._target.__qualname__


