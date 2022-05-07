import sys
import os
import _thread


# generic constants:
GLOBAL_NAME = 'multitools_2'
DEFAULT_ENCODING = sys.getdefaultencoding()
NULL_BYTE = b"\x00"
def f(): ...
BUILTINS_DICT = f.__builtins__
del f

# submodule names:
MODNAME_EXTERNAL = GLOBAL_NAME + '.external'
MODNAME_PROCESS = GLOBAL_NAME + '.process'

# functions that do nothing:
NO_OP_READER = lambda: None
NO_OP_WRITER = lambda data: None
NO_OP_THREAD_CALLABLE = lambda th, *args, **kwargs: None

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

# event-related constants:
EVENT_CALL = 'call'
EVENT_LINE = 'line'
EVENT_RETURN = 'return'
EVENT_EXCEPTION = 'exception'
EVENT_OPCODE = 'opcode'

# thread/process pipe messaging
GET_PROC_ATTR = "self.{0}"  # .format(name)
SET_PROC_ATTR = "self.{0}={1}"  # .format(name, literal)
CALL_PROC_METHOD_NOARGS = "self.{0}()"  # .format(name)
CALL_PROC_METHOD_ARGS = "self.{0}(*{1}))"  # .format(name, (*args))
GET_THREAD_ATTR = "self.__threads__[{0}].{1}"  # .format(t_id, name)
SET_THREAD_ATTR = "self.__threads__[{0}].{1}={2}"  # .format(t_id, name, literal)
CALL_THREAD_METHOD_NOARGS = "self.__threads__[{0}].{1}()"  # .format(t_id, name)
CALL_THREAD_METHOD_ARGS = "self.__threads__[{0}].{1}(*{2})"  # .format(t_id, name, (*args))
ASK_EXECUTE = "self._run_local()"
ASK_LAST_ERR = "(sys.exc_info()[0], repr(sys.exc_info()[1].args))"

# thread/process messaging errors:
TPM_ERR_PERMISSION = "\x00P"

# other runtime-related contants:
def f(*args, **kwargs): ...
NULL_CODE = f.__code__  # Code object that does nothing and accepts any arguments.
del f

