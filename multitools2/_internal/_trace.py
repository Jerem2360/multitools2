import sys

"""
Basic features for an advanced custom tracing
system.
"""


_trackers = {}
_trace_opcodes = False


class Tracker:
    """
    Tracing and Profiling function type. Call set_trace() and set_profile() to set accordingly.
    This **private** type implements special behaviour.
    """

    __slots__ = [
        '__func__',
        '__ancestors__'
    ]

    def __init__(self, func):
        self.__func__ = func
        self.__ancestors__ = {}

    def __call__(self, frame, event, arg):
        return self.__func__(frame, event, arg)

    def _trace(self, frame, event, arg):
        if frame in self.__ancestors__:
            ancestor = self.__ancestors__[frame]
        else:
            ancestor = self.__ancestors__[None]

        res = self.__func__(frame, event, arg)

        if not callable(ancestor):
            return self._trace

        if isinstance(res, Exception):
            try:
                raise res
            except:
                print(f"Exception raised in tracker function '{self.__func__.__qualname__}':", file=sys.stderr)
                sys.excepthook(*sys.exc_info())
                raise SystemExit(1)

        if res is None:
            res = arg

        try:
            ancestor(frame, event, res)
        except:
            print(f"Exception raised in tracker function '{ancestor.__qualname__}':", file=sys.stderr)
            sys.excepthook(*sys.exc_info())
            raise SystemExit(1)

        return self._trace

    def _profile(self, frame, event, arg):
        ancestor = self.__ancestors__.get("profile", None)

        res = self.__func__(frame, event, arg)

        if not callable(ancestor):
            return

        if res is None:
            res = arg

        ancestor(frame, event, res)

    def set_trace(self, frame=None, /):
        if frame is None:
            frame = sys._getframe(1)

        if frame.f_trace is not self._trace:
            self.__ancestors__[frame] = frame.f_trace
            frame.f_trace = self._trace

        if sys.gettrace() is not self._trace:
            self.__ancestors__[None] = sys.gettrace()
            sys.settrace(self._trace)

    def set_profile(self):
        if sys.getprofile() is not self._profile:
            self.__ancestors__["profile"] = sys.getprofile()
            sys.setprofile(self._profile)

    def __dir__(self):
        res = list(super().__dir__())
        res.pop(res.index("_trace"))
        res.pop(res.index("_profile"))
        return tuple(res)

    def __repr__(self):
        return f"<tracking function '{self.__func__.__qualname__}' at {hex(id(self))}>"


class SafeTracker:
    """
    Public Tracing function type. Can be used as a decorator.
    This implements a new tracing and profiling system (without
    disallowing the use of the default one).
    The custom tracing system allows multiple functions to
    trace code execution simultaneously, without colliding with
    each other.
    """
    __slots__ = [
        '__func__'
    ]

    def __init__(self, function):
        self.__func__ = function

    def __call__(self, frame, event, arg):
        self.__func__(frame, event, arg)

    def __repr__(self):
        return f"<tracking function '{self.__func__.__qualname__}' at {hex(id(self))}>"

    def register(self, event):
        """
        Register a tracing function for a given event.
        """
        if event not in _trackers:
            _trackers[event] = []
        _trackers[event].append(self)

    def unregister(self, event):
        """
        Unregister a tracing function for a given event.
        """
        if event in _trackers and self in _trackers[event]:
            _trackers[event].pop(_trackers[event].index(self))


class TrackEvent(str):
    """
    A separate type for tracing events.
    """


c_call = TrackEvent('c_call')
c_return = TrackEvent('c_return')
call = TrackEvent('call')
line = TrackEvent('line')
return_ = TrackEvent('return')
exception = TrackEvent('exception')
opcode = TrackEvent('opcode')

