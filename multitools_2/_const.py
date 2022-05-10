import sys
import os
import _thread

from ._local import *


__all__ = [
    "ANDROID",
    "MS_WINDOWS",

    "SHELL",

    "GLOBAL_NAME",
    "DEFAULT_ENCODING",
    "NULL_BYTE",
    "BUILTINS_DICT",
    "NULL",

    "MODNAME_EXTERNAL",
    "MODNAME_PROCESS",

    "NO_OP_READER",
    "NO_OP_WRITER",
    "NO_OP_THREAD_CALLABLE",
    "NO_OP_TRACER",
    "NO_OP",
    "NO_OP_PROCESS_MAIN",

    "OS_PATHSEP",
    "STD_PATHSEP",

    "DLL_EXTENSION",
    "DLL_PARENT_MODULE_NAME",
    "DLLIMPORT_FROM_NAME",

    "TSTATE_INITIALIZED",
    "TSTATE_RUNNING",
    "TSTATE_FINALIZED",
    "MAIN_THREAD_ID",

    "MAIN_PROCESS_ID",

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


# platform-related constants:
MS_WINDOWS = (sys.platform == "win32")
ANDROID = hasattr(sys, 'getandroidapilevel')

SHELL = os.environ.get('COMSPEC', 'cmd.exe') if MS_WINDOWS else '/system/bin/sh' if ANDROID else '/bin/sh'


@customPath(GLOBAL_NAME)
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


# generic constants:
DEFAULT_ENCODING = sys.getdefaultencoding()
NULL_BYTE = b"\x00"
NULL = _NullType()
def f(): ...
# noinspection PyUnresolvedReferences
BUILTINS_DICT = f.__builtins__
del f

# submodule names:
MODNAME_EXTERNAL = GLOBAL_NAME + '.external'
MODNAME_PROCESS = GLOBAL_NAME + '.process'

# functions that do nothing:
NO_OP_READER = lambda: None
NO_OP_WRITER = lambda data: None
NO_OP_THREAD_CALLABLE = lambda th, *args, **kwargs: None
NO_OP_PROCESS_MAIN = lambda proc, *args, **kwargs: None
NO_OP_TRACER = lambda frame, event, args: NO_OP_TRACER
NO_OP = lambda *args, **kwargs: None

# path-related constants
OS_PATHSEP = os.sep
STD_PATHSEP = '/'

# dll importing constants:
DLL_EXTENSION = '.dll' if sys.platform == 'win32' else '.so'
DLL_PARENT_MODULE_NAME = "<dll loader module>"
DLLIMPORT_FROM_NAME = GLOBAL_NAME + '.dll'

# thread-related constants:
TSTATE_INITIALIZED = 0
TSTATE_RUNNING = 1
TSTATE_FINALIZED = 2
MAIN_THREAD_ID = _thread.get_ident()  # we are supposedly in the main thread

# process-related constants:
MAIN_PROCESS_ID = os.getpid()  # we are supposedly in the main process

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

# thread/process messaging errors:
TPM_ERR_PERMISSION = "\x00P"

# other runtime-related contants:
def f(*args, **kwargs): ...
NULL_CODE = f.__code__  # Code object that does nothing and accepts any arguments.
del f

