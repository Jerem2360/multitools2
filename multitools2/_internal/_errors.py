"""
Internal API module aiming to upgrade python's exception handling
mechanisms.
"""


import sys
import types

from . import hooks


_excluded_frames = []


class ExceptionConfiguration(BaseException):
    """
    Object that defines what to do when an exception is raised.
    Attributes that don't start with '_' can be customized.

    "trace_depth": Defines the number of frames, following and including the one
        where the exception was raised, that should not be printed to sys.stderr
        with the exception.

    "suppress_cause": Whether to remove completely the cause of the exception.

    "suppress_context": Whether to remove completely the context of the exception.

    "tb_exclude": Frames that won't show on the traceback of the exception.
        If this setting would make the traceback empty, it is ignored.

    This mechanism only changes exception tracebacks when they're about to
    be printed to sys.stderr. This means that when the exception is caught,
    it will contain the full original traceback, and not the rearranged one,
    as opposed to what you might expect. This avoids losing possibly precious
    information about the cause of the error. It also preserves compatibility
    with other python modules.

    Note:
        This class cannot be raised directly.
    """

    def __init__(self):
        self.trace_depth = 0  # depth at which to start tracing
        self.suppress_context = False
        self.suppress_cause = False
        self.tb_exclude = []
        self._cause = None  # cause of the exception, don't touch.
        self._frame = None  # frame where the exception was raised. Don't touch.

    def __repr__(self):
        return f"<ExceptionConfiguration at {hex(id(self))}, trace_depth={self.trace_depth}, suppress_cause={self.suppress_cause}, suppress_context={self.suppress_context}>"

    def __str__(self):
        return repr(self)


class HideFrame:
    """
    Context manager that hides the current frame from the
    traceback of any exceptions that occur in its body.

    example:

    def f():
        raise TypeError("test")

    def f1():
        with HideFrame():
            f()

    f1()

    output:

    Traceback (most recent call last):
      File "test.py", line 8, in <module>
        f1()
      File "test.py", line 2, in f
        raise TypeError
    TypeError: test

    Here, the scope in which the call to f() was wrapped in a with
    statement, wasn't printed to the console because of the HideFrame() call.

    Hiding all scopes in the call chain will result in an empty traceback and,
    as expected, no traceback will be printed.
    """
    def __init__(self, _d=0):
        from . import runtime
        self._frame = runtime.call_stack[_d+1]

    def __enter__(self):
        _excluded_frames.append(id(self._frame))

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type or exc_val or exc_tb:
            return
        try:
            _excluded_frames.pop(_excluded_frames.index(id(self._frame)))
        except:
            pass


class ExceptionManager:
    """
    Decorator class that makes a callable capable of configuring a raised exception.

    If the decorated object is a class, it must inherit from ExceptionConfiguration. Its
    constructor should then set the appropriate public attributes.

    If the decorated object is a function, it must create a new ExceptionConfiguration object,
    fill in its public members and return it. The signature doesn't matter.

    When calling the decorated callable, though, an optional 'cause' positional argument is
    available as its first parameter. It allows to explicitly set the exception cause,
    which must be an exception object. It would look as follows:
        manager([cause], <manager arguments>)

    Usage:
    raise Exception(...) from manager(...)

    Note:
        If an object other than en exception or what is returned by this class is used in
        the 'from' clause, the raised exceptions cause will get suppressed.
    """

    def __init__(self, fn):
        self._fn = fn

    def __call__(self, cause=None, *args, **kwargs):
        from . import runtime
        frame = runtime.call_stack[1]
        config = self._fn(*args, **kwargs)
        if not isinstance(config, ExceptionConfiguration):
            config = ExceptionConfiguration()
        config._frame = frame

        if isinstance(cause, type) and issubclass(cause, BaseException):
            cause = cause()
        if not (isinstance(cause, BaseException) or (cause is None)):
            cause = None
        config._cause = cause
        return config

    def __repr__(self):
        return f"<ExceptionManager '{self._fn.__module__}.{self._fn.__qualname__}' at {hex(id(self))}>"


@ExceptionManager
def configure(trace_depth=0, suppress_cause=False, suppress_context=False, tb_exclude=[]):
    """
    A basic exception manager that covers every possible setting for an exception.
    Values are passed to the config as they were passed in to this call.
    """

    config = ExceptionConfiguration()
    config.trace_depth = trace_depth
    config.suppress_cause = suppress_cause
    config.suppress_context = suppress_context
    config.tb_exclude = tb_exclude
    return config


def print_full_traceback(etype, evalue, tb):
    """
    Print the full original traceback of an exception to sys.stderr.
    This only applies to exceptions customized with exception managers.
    Other exceptions get printed normally to sys.stderr.
    """
    sys.__excepthook__(etype, evalue, tb)


def _err_depth(err: BaseException, depth):
    err.__configuration__ = configure(None, trace_depth=depth + 1)
    _special_case(err)
    # noinspection PyTypeChecker
    _apply_config(err)
    return err


def _special_case(err: BaseException):
    # noinspection PyUnresolvedReferences
    err.__configuration__._noprint = True
    _excluded_frames.clear()  # it's the user's fault, so we ignore hidden frames.


def _build_traceback(frame, _exframes=True):
    _next = None
    tb = None

    while True:
        if _exframes and (id(frame) not in _excluded_frames):
            tb = types.TracebackType(_next, frame, frame.f_lasti, frame.f_lineno)
            _next = tb
        frame = frame.f_back
        if frame is None:
            break

    return tb


def _apply_config(exc):
    config = exc.__configuration__
    if config.suppress_context:
        exc.__context__ = None
    if config.suppress_cause:
        exc.__cause__ = None

    frame = config._frame

    depth = -config.trace_depth
    while depth:
        if frame is None:
            break
        frame = frame.f_back
        depth += 1
    if frame is None:
        raise _err_depth(IndexError("Call stack is not deep enough."), 4)
    config._frame = frame


def _trace2(frame, *exc_info):
    exc = exc_info[1]

    if isinstance(exc, ExceptionConfiguration):
        # ExceptionConfiguration and its subclasses cannot be raised
        raise _err_depth(TypeError(f"'{type(exc).__name__}' cannot be raised."), 3)
    if not isinstance(exc.__cause__, ExceptionConfiguration):
        return

    config = exc.__cause__
    if exc.__cause__ != config._cause:
        exc.__cause__ = config._cause

    exc.__configuration__ = config
    _apply_config(exc)


hooks._exceptional_handler = _trace2  # function that can handle very special cases
hooks.settrace(_trace2, 'exception')


def _excepthook(etype, evalue, tb):
    if hasattr(evalue, '__configuration__') and isinstance(evalue.__configuration__, ExceptionConfiguration):
        config = evalue.__configuration__

        for f in config.tb_exclude:
            _excluded_frames.append(id(f))

        tb = _build_traceback(config._frame)
        evalue.__traceback__ = tb
    sys.__excepthook__(etype, evalue, tb)


sys.excepthook = _excepthook
