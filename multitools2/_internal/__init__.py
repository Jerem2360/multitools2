import sys


__all__ = [
    '__NAME__',
    '__DEBUG__',
    '__ROOT__',
    '__trace_refs__',
    'IS_SYSTEM_x64',
    'MS_WIN32',
    'MS_WIN64',
    'ANDROID',
    '__APPLE__',

    'POS_ARG_ERR',
    'TYPE_ERR',
    'NOT_CALLABLE_ERR',
    'ATTRIBUTE_ERR',

    'TPFLAGS_HEAPTYPE',

    'scope_at',
    'trace_opcodes',
]

from typing import TypeVar

TPFLAGS_HEAPTYPE = 1 << 9

STATIC_OBJECTS = [
    b'',
    '',
]

from . import _trace

def trace_opcodes():
    """
    Enable tracing of opcodes.
    For performance reasons, this is disabled by default.
    """
    _trace._trace_opcodes = True

@_trace.Tracker
def __tracker__(frame, event, args):
    """
    Track everything that happens in the interpreter.
    frame, event and args are the tracing and profiling parameters.
    ** don't touch! **
    """
    try:
        frame.f_trace_opcodes = _trace._trace_opcodes
        trackers = _trace._trackers.get(_trace.TrackEvent(event), [])
    except NameError:
        return
    for tracker in trackers:
        if callable(tracker):
            tracker(frame, event, args)


del _trace

_path_sep = '\\' if sys.platform == 'win32' else '/'

i = -1
_f = None
while True:
    i += 1
    try:
        _f = sys._getframe(i)
    except ValueError:
        break
    if _f.f_code.co_filename in (
            "<frozen importlib._bootstrap>",
            "<frozen importlib._bootstrap_external>",
            __file__,
            __file__.replace(f"_internal{_path_sep}__init__.py", "__init__.py")
    ):
        continue
    break


__tracker__.set_trace(_f)
__tracker__.set_profile()

del _f, _path_sep, i


__NAME__ = ''  # real value of type str assigned later at runtime
__DEBUG__ = True
__ROOT__ = ...  # real value of type module assigned later at runtime

# same as the Py_TRACE_REFS macro of the C api: https://github.com/python/cpython/blob/main/Misc/SpecialBuilds.txt
__trace_refs__ = hasattr(sys, 'getobjects')  # Py_DEBUG

IS_SYSTEM_x64 = sys.maxsize > 2 ** 31 - 1  # if the host machine has a 64-bit system

MS_WIN32 = sys.platform == "win32"  # if the host is Windows machine
MS_WIN64 = MS_WIN32 and IS_SYSTEM_x64  # if the host is a Windows x64 machine
ANDROID = hasattr(sys, 'getandroidapilevel')

__APPLE__ = sys.platform == "darwin"  # if the host is a MacOSx machine


# exception messages:
POS_ARG_ERR = "{0} accepts {1} positional argument(s), but {2} were given."
TYPE_ERR = "Expected type '{0}', got '{1}' instead."
NOT_CALLABLE_ERR = "'{0}' object is not callable."
ATTRIBUTE_ERR = "'{0}' object has no attribute '{1}'."


_T = TypeVar('_T')


def scope_at(module, scope=''):
    mod = sys.modules[module]
    nodes = scope.split('.') if scope else []
    attr = mod
    for node in nodes:
        attr = getattr(attr, node)

    def _inner(target: _T) -> _T:
        setattr(attr, target.__name__, target)
        if len(nodes):
            target.__qualname__ = '.'.join(nodes) + '.' + target.__name__
        else:
            target.__qualname__ = target.__name__
        target.__module__ = module
        return target

    return _inner

