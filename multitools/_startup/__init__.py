from . import _onexit


def onexit_register(func):
    _onexit._register(func, func.__qualname__)


del _onexit

