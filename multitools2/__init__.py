import types
import sys

from . import _internal

# avoid circular import in _internal.errors
_internal.__NAME__ = __name__
_internal.__ROOT__ = sys.modules[__name__]

from ._internal import errors as _err




def excepthook(etype: type[BaseException], evalue: BaseException, tb: types.TracebackType):
    """
    The custom excepthook used by multitools.
    It is exposed here so users can call it
    from their own excepthooks.
    """
    # return _err._excepthook(etype, evalue, tb)

