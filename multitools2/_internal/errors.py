"""

"""
"""
Most functionalities are ok.
The technique for raising ContextError when an unraisable
is raised is far from perfect, could be greatly upgraded.
"""

import sys
import traceback
import types

from . import hooks
from . import runtime


from . import *


# flags:
_INVALID_UNRAISABLE = 0b1
_INVALID_REPLACE = 0b10


# global variables:
_excluded_frames = []


# public stuff:
class ExceptionConfiguration:
    def __init__(self):

        self.depth = 0
        self.suppress_context = False
        self.suppress_cause = False
        self.tb_exclude = []
        self.cause = None


class ExceptionConfigurator:
    def __init__(self, _func):
        self._func = _func

    def __call__(self, *args, **kwargs):
        cause = kwargs.pop('cause', None)
        if cause and isinstance(cause, type) and issubclass(cause, BaseException):
            cause = cause()
        frame = runtime.call_stack[1]

        result = self._func(*args, **kwargs)
        if not isinstance(result, ExceptionConfiguration):
            result = ExceptionConfiguration()
        result.cause = cause
        # print('res:', result)
        return _ConfigHolder(result, frame)


@ExceptionConfigurator
def configure(
        depth=0,
        suppress_context=False,
        suppress_cause=False,
        tb_exclude=[],
      ):
    """

    """
    config = ExceptionConfiguration()
    config.depth = depth
    config.suppress_context = suppress_context
    config.suppress_cause = suppress_cause
    config.tb_exclude = tb_exclude
    return config


@runtime.scope_at(__ROOT__)
class ContextError(Exception): ...


if MS_WIN32:
    @runtime.scope_at(__ROOT__)
    class InvalidHandleError(OSError): ...


# private stuff:

def _build_config(exc):
    config = exc.__configuration__._config
    frame = exc.__configuration__._frame

    if config.suppress_context:
        exc.__context__ = None
    if config.suppress_cause:
        exc.__cause__ = None

    depth = -config.depth
    while depth:
        if frame is None:
            break
        frame = frame.f_back
        depth += 1

    if frame is None:
        raise _err_depth(IndexError("Call stack is not deep enough."), 4)
    exc.__configuration__._frame = frame
    exc.__configuration__._excluded_frames.extend(_excluded_frames)


def _trace_exceptions(frame, *exc_info):
    exc_val = exc_info[1]
    if isinstance(exc_val, _ConfigHolder):
        # tell the excepthook how to handle our case:
        exc_val._invalidity_flag = _INVALID_UNRAISABLE | _INVALID_REPLACE
        return

    if not isinstance(exc_val.__cause__, _ConfigHolder):
        return
    config = exc_val.__cause__._config

    exc_val.__configuration__ = exc_val.__cause__
    exc_val.__cause__ = config.cause

    exc_val.__configuration__._etype = exc_info[0]

    _build_config(exc_val)
    # print(exc_val.__configuration__._frame)

    # print('exception:', exc_info, exc_val.__cause__, exc_val.__configuration__)


hooks.settrace(_trace_exceptions, hooks.EVENT_EXCEPTION)


def _build_traceback(frame, excluded_frames):
    _next = None
    tb = None

    while True:
        if id(frame) not in excluded_frames:
            tb = types.TracebackType(_next, frame, frame.f_lasti, frame.f_lineno)
            _next = tb
        frame = frame.f_back
        if frame is None:
            break

    return tb


def _excepthook(exc_type, exc_value, _traceback):
    # print(dir(exc_value))
    # Error modifying machinery.
    # If an exception is raised where it shouldn't be,
    # we print accurate information to sys.stderr.
    _invalidity_flags = getattr(exc_value, '_invalidity_flag', 0)
    if _invalidity_flags & _INVALID_UNRAISABLE:
        # Here, _ConfigHolder's inheritance from ContextError comes in very handy:
        # it lets the user catch its modified version as a ContextError: the exception
        # printed to sys.stderr.
        if _invalidity_flags & _INVALID_REPLACE:
            err = ContextError(f"Cannot raise '{exc_type.__name__}' directly.")
            return sys.__excepthook__(ContextError, err, _traceback)

        # maybe users should be allowed to raise these things anyway.
        # depends on if it's worth it
        print("The following invalid exception was thrown:", file=sys.stderr)

    # traceback customizing machinery:
    elif hasattr(exc_value, '__configuration__') and isinstance(exc_value.__configuration__, _ConfigHolder):
        _traceback = _build_traceback(exc_value.__configuration__._frame, exc_value.__configuration__._excluded_frames)
        exc_value.__traceback__ = _traceback

    sys.__excepthook__(exc_type, exc_value, _traceback)


sys.excepthook = _excepthook


# This inherits ContextError instead of BaseException to be more user-friendly:
class _ConfigHolder(ContextError):
    def __init__(self, config, frame):
        if frame.f_code.co_name == '__main__':
            raise ContextError("Cannot configure exceptions raised from the main code.")

        self._config = config
        self._frame = frame
        self._etype = None
        self._excluded_frames = []

    def __str__(self):
        _flags = getattr(self, '_invalidity_flags', 0)
        if _flags:
            msg = f"Cannot raise '{type(self).__name__}' directly."
            return repr((msg,))
        return repr(self)

    def __repr__(self):
        _flags = getattr(self, '_invalidity_flags', 0)
        if _flags:
            msg = f"Cannot raise '{type(self).__name__}' directly."
            return f"ContextError({repr(msg)})"
        if self._etype:
            return f"<config for exception '{self._etype.__name__}' in code {self._frame.f_code.co_name} at {hex(id(self))}>"
        return f"<config for an exception in code {self._frame.f_code.co_name} at {hex(id(self))}>"


def _err_depth(err: BaseException, depth=0, cause=None):
    if depth+1 >= len(runtime.call_stack):
        return err
    err.__configuration__ = configure(depth=depth+1, cause=cause)
    # noinspection PyTypeChecker
    _build_config(err)
    err.__configuration__._excluded_frames.clear()
    return err


class _FrameHider:
    def __enter__(self):
        try:
            self._frame = runtime.call_stack[1]
            _excluded_frames.append(id(self._frame))
        except:
            self._frame = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._frame is None:
            return
        if exc_type or exc_val or exc_tb:
            return
        _excluded_frames.pop(_excluded_frames.index(id(self._frame)))


# public members:
frame_mask = _FrameHider()
"""
Context manager.
The current frame will get removed from the traceback of any 
exception that occurs within its scope.
"""

