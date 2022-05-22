import sys


ATTRIB_ERR_STR = "'{0}' object has no attribute '{1}'."
POS_ARGCOUNT_ERR_STR = "{0} accepts {1} positional argument(s), but {2} were given."


def _NoPath(error):
    error.__module__ = "builtins"
    return error


def latest():
    return sys.exc_info()[0](*sys.exc_info()[1].args)


@_NoPath
class ExternalReferenceError(ImportError):
    """
    Unresolved external symbol.
    """
    def __init__(self, *args, source=None, wrong_ref=None):
        if (source is None) or (wrong_ref is None):
            super().__init__(*args)
            return
        if len(args) > 0:
            super().__init__(*(str(arg).format(source, wrong_ref) for arg in args))
            return
        super().__init__(f"Failed to resolve external reference '{wrong_ref}' for '{source}' object.")


@_NoPath
class NULLReferenceError(ValueError):
    """
    Referred to an invalid NULL instance.
    """
    def __init__(self, *args, **kwargs):
        if len(args) >= 1:
            super().__init__(*args)
            return
        super().__init__("NULL reference.")


@_NoPath
class ThreadError(BaseException):
    pass


@_NoPath
class ThreadStateError(ThreadError):
    def __init__(self, *args, expected=1, got=0):
        expected_s = ""
        match expected:
            case 0:
                expected_s = "'Initialized'"
            case 1:
                expected_s = "'Running'"
            case 2:
                expected_s = "'Finalized'"
            case _:
                expected_s = str(expected)

        got_s = ""
        match got:
            case 0:
                got_s = "'Initialized'"
            case 1:
                got_s = "'Running'"
            case 2:
                got_s = "'Finalized'"
            case _:
                got_s = str(got)

        if len(args) == 0:
            super().__init__(f"Invalid thread state for operation: expected {expected_s} state, got {got_s} instead.")
            return


@_NoPath
class ProcessError(BaseException):
    pass


@_NoPath
class ProcessStartupError(ProcessError):
    def __init__(self, *args, reason=None):
        if reason is None:
            super().__init__(*args)
        else:
            super().__init__(*args, f"(reason: {reason})")


@_NoPath
class ProcessStateError(ProcessError):
    pass


@_NoPath
class OutOfScopeError(ProcessLookupError):
    def __init__(self, *args):
        if len(args) > 0:
            super().__init__(*args)
            return
        super().__init__("Target is out of scope of this process.")

