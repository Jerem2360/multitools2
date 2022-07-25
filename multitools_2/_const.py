import sys
import os
import _thread
import pickle as _pickle
from typing import Callable


# platform-related constants:
MS_WINDOWS = (sys.platform == "win32")
ANDROID = hasattr(sys, 'getandroidapilevel')


if MS_WINDOWS:
    from ._win32 import getpid as _getpid
else:
    from os import getpid as _getpid


def _CustomPath(value):
    def _wrap(x):
        x.__module__ = value
        return x

    return _wrap


__all__ = [
    "ANDROID",
    "MS_WINDOWS",

    "SHELL",
    "SHELL_OPT",

    "GLOBAL_NAME",
    "DEFAULT_ENCODING",
    "NULL_BYTE",
    "BUILTINS_DICT",
    "NULL",

    "MODNAME_EXTERNAL",
    "MODNAME_PROCESS",
    "MODNAME_IO",

    "SHORT_TRUE",
    "SHORT_FALSE",
    "SHM_SAFE_NAME_LENGTH",
    "SHM_NAME_PREFIX",

    "NO_OP_READER",
    "NO_OP_WRITER",
    "NO_OP_THREAD_TARGET",
    "NO_OP_TRACER",
    "NO_OP",
    "NO_OP_PROCESS_TARGET",

    "OS_PATHSEP",
    "STD_PATHSEP",

    "DLL_EXTENSION",
    "DLL_PARENT_MODULE_NAME",
    "DLLIMPORT_FROM_NAME",

    "STATE_INITIALIZED",
    "STATE_RUNNING",
    "STATE_TERMINATED",
    "MAIN_THREAD_ID",
    "MAIN_PROCESS_ID",
    "MAIN_PROC_ENV_NAME",
    "RESERVED_PROCESSES",
    "ENV_THREADS",
    "ENV_PROCS",
    "ENV_PY_PROCS",
    "CALL_WAIT_TIMEOUT",

    "EVENT_CALL",
    "EVENT_LINE",
    "EVENT_RETURN",
    "EVENT_EXCEPTION",
    "EVENT_OPCODE",

    "GET_PROC_ATTR",
    "SET_PROC_ATTR",
    "CALL_PROC_METHOD_NOARGS",
    "CALL_PROC_METHOD_ARGS",
    "GET_THREAD_ATTR",
    "SET_THREAD_ATTR",
    "CALL_THREAD_METHOD_NOARGS",
    "CALL_THREAD_METHOD_ARGS",
    "THREAD_EXECUTE",
    "ASK_LAST_ERR",

    "TPM_ERR_PERMISSION",

    "NULL_CODE",
]


GLOBAL_NAME = 'multitools_2'
GLOBAL_PATH = __file__.removesuffix('/_const.')


SHELL = os.environ.get('COMSPEC', 'cmd.exe') if MS_WINDOWS else '/system/bin/sh' if ANDROID else '/bin/sh'
SHELL_OPT = '/' if MS_WINDOWS else '-'


def _as_named_func(func, module, name) -> Callable:
    func.__name__ = name
    func.__module__ = module
    func.__qualname__ = f"{module}.{name}"
    return func


def _as_named_func2(func, name, set_) -> Callable:
    func.__name__ = name
    func.__qualname__ = name
    if set_:
        setattr(sys.modules[GLOBAL_NAME], name, func)
    return func


# generic constants:
DEFAULT_ENCODING = sys.getdefaultencoding()
NULL_BYTE = b"\x00"
def f(): ...
# noinspection PyUnresolvedReferences
BUILTINS_DICT = f.__builtins__
del f

# submodule names:
MODNAME_EXTERNAL = GLOBAL_NAME + '.external'
MODNAME_PROCESS = GLOBAL_NAME + '.process'
MODNAME_IO = GLOBAL_NAME + '.io'
MODNAME_RUNTIME = GLOBAL_NAME + '.runtime'

# functions that do nothing:
_no_op = 'no_op'
_NO_OP = lambda *args, **kwargs: None
_NO_OP_READER = lambda: None
_NO_OP_WRITER = lambda data: None
_NO_OP_THREAD_CALLABLE = lambda th, *args, **kwargs: None
_NO_OP_PROCESS_TARGET = lambda proc, *args, **kwargs: None
_NO_OP_TRACER = lambda frame, event, args: NO_OP_TRACER

NO_OP = _as_named_func(_NO_OP, GLOBAL_NAME, _no_op)
NO_OP_READER = _as_named_func(_NO_OP_READER, GLOBAL_NAME, _no_op)
NO_OP_WRITER = _as_named_func(_NO_OP_WRITER, GLOBAL_NAME, _no_op)
NO_OP_THREAD_TARGET = _as_named_func(_NO_OP_THREAD_CALLABLE, GLOBAL_NAME, _no_op)
NO_OP_PROCESS_TARGET = _as_named_func(_NO_OP_PROCESS_TARGET, GLOBAL_NAME, _no_op)
NO_OP_TRACER = _as_named_func(_NO_OP_TRACER, GLOBAL_NAME, _no_op)


# path-related constants
OS_PATHSEP = os.sep
STD_PATHSEP = '/'

# dll importing constants:
DLL_EXTENSION = '.dll' if sys.platform == 'win32' else '.so'
DLL_PARENT_MODULE_NAME = "<dll loader module>"
DLLIMPORT_FROM_NAME = GLOBAL_NAME + '.dll'

# thread-related constants:
STATE_INITIALIZED = 0
STATE_RUNNING = 1
STATE_TERMINATED = 2
CALL_WAIT_TIMEOUT = 2

# binary constants:
SHORT_TRUE = (1).to_bytes(2, 'big', signed=False)
SHORT_FALSE = (0).to_bytes(2, 'big', signed=False)

# shared memory constants:
SHM_SAFE_NAME_LENGTH = 14
SHM_NAME_PREFIX = 'wnsm_' if MS_WINDOWS else '/psm_'

# process-related constants:
MAIN_PROC_ENV_NAME = GLOBAL_NAME + ':MAIN_PROC'
# small trick to always have the main process' id (See file 'runtime/_process.py' for details):
MAIN_PROCESS_ID = int(os.environ.get(MAIN_PROC_ENV_NAME, str(_getpid())))
MAIN_THREAD_ID = _thread.get_native_id()
RESERVED_PROCESSES = (0, 4)  # processes that cannot be opened.
ENV_THREADS = GLOBAL_NAME + '_THREADS'
ENV_PROCS = GLOBAL_NAME + '_PROCS'
ENV_PY_PROCS = GLOBAL_NAME + '_PY_PROCS'

# event-related constants:
EVENT_CALL = 'call'
EVENT_LINE = 'line'
EVENT_RETURN = 'return'
EVENT_EXCEPTION = 'exception'
EVENT_OPCODE = 'opcode'

# thread/process pipe messaging
GET_PROC_ATTR = "Proc.Getattr {0}"  # .format(name)
SET_PROC_ATTR = "Proc.Setattr {0} {1}"  # .format(name, literal)
CALL_PROC_METHOD_NOARGS = "Proc.CallNoargs {0}"  # .format(name)
CALL_PROC_METHOD_ARGS = "Proc.Call {0} {1}"  # .format(name, (*args))
GET_THREAD_ATTR = "Thread:{0}.Getattr {1}"  # .format(t_id, name)
SET_THREAD_ATTR = "Thread:{0}.Setattr {1} {2}"  # .format(t_id, name, literal)
CALL_THREAD_METHOD_NOARGS = "Thread:{0}.CallNoargs {1}"  # .format(t_id, name)
CALL_THREAD_METHOD_ARGS = "Thread:{0}.Call {1} {2}"  # .format(t_id, name, (*args))
THREAD_EXECUTE = "Thread:{0}.Start"
ASK_LAST_ERR = "ExcInfo"
MSG_EXIT = "Exit:{0}"  # .format(code)

# thread/process messaging errors:
TPM_ERR_PERMISSION = "\x00P"

# other runtime-related contants:
def f(*args, **kwargs): ...
NULL_CODE = f.__code__  # Code object that does nothing and accepts any arguments.
del f


@_CustomPath(GLOBAL_NAME)
class _NullType:
    __qualname__ = "NULL_t"

    def __repr__(self):
        return "NULL"

    def __int__(self):
        return 0

    def __float__(self):
        return 0.0

    def __complex__(self):
        return complex(0, 0)

    def __str__(self):
        return "NULL"

    def __bytes__(self):
        return b'\x00'

    def __eq__(self, other):
        tp = type(other)
        if tp in (int, float, complex, bytes, str):
            return other == tp(self)
        return False


NULL = _NullType()

