import sys


EVENT_CALL = 'call'
EVENT_LINE = 'line'
EVENT_RETURN = 'return'
EVENT_EXCEPTION = 'exception'
EVENT_OPCODE = 'opcode'
EVENT_ALL = '*'  # all events


_traces = {
    'call': [],
    'line': [],
    'return': [],
    'exception': [],
    'opcode': [],
}

# special trace function that should never ever cause exceptions:
_exceptional_handler = None  # real value of type Callable[[FrameType, ...], None] set later in _errors.py


# special case for errors._trace
def _has_special_case(err: BaseException):
    return hasattr(err, '__configuration__') and getattr(err.__configuration__, '_noprint', False)


def _run_event(frame, event, args):
    res_total = True
    to_run = _traces[event]
    for fn in to_run:
        try:
            res = fn(frame, *args)
        except SystemExit:
            raise
        except BaseException as e:
            tb = sys.exc_info()[2]
            while True:
                if tb.tb_next is None:
                    break
                tb = tb.tb_next
            frame = tb.tb_frame
            no_print = False
            if event != 'exception':
                no_print = _run_event(frame, 'exception', sys.exc_info())
            elif _exceptional_handler is not None:
                # noinspection PyCallingNonCallable
                _exceptional_handler(frame, *sys.exc_info())

            if _has_special_case(e):
                # noinspection PyUnresolvedReferences
                no_print = e.__configuration__._noprint
            if not no_print:
                print(f"Error in trace function '{fn.__module__}.{fn.__qualname__}':", file=sys.stderr)
            raise

        if isinstance(res, bool):
            res_total = res and res_total
    return res_total


def _trace(frame, event, args):
    frame.f_trace_opcodes = True
    _run_event(frame, event, args)
    return _trace

sys.settrace(_trace)


def settrace(tracefunc, events):
    """
    Set the current tracing function for the main thread.
    This does not affect other threads.
    """
    if events == '*':
        for evn, ev in _traces.items():
            ev.append(tracefunc)
        return

    if not isinstance(events, tuple):
        events = (events,)

    for ev in events:
        if ev not in _traces:
            raise TypeError(f"'{ev}' is not a trackable event.")
        _traces[ev].append(tracefunc)


def gettrace(event='*'):
    if event == '*':
        res = []
        for evn, ev in _traces.items():
            res.extend(ev)
        return res
    return _traces[event]


def _excepthook(*exc_info): ...

