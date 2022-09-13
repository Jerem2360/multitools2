"""
Data structures that allow ultra-customizable errors.
"""


import sys

from .. import *
from .._typeshed import *


### -------- Constants -------- ###
ATTR_ERR_STR = "'{0}' object has no attribute '{1}'."
POS_ARGCOUNT_ERR_STR = "{0} accepts {1} positional argument(s), but {2} were given."
TYPE_ERR_STR = "Expected type '{0}', got '{1}' instead."
NOT_CALLABLE_ERR_STR = "'{0}' object is not callable."


### -------- Traceback customization machinery -------- ###

def err_depth(etype, *args, depth=0, **kwargs):
    return AdvancedException.force_depth(etype(*args, **kwargs), depth=depth+1, _raise_depth=1)


_old_excepthook = sys.excepthook

def _excepthook(etype, evalue, tb):
    """
    Except hook that modifies the exception traceback when needed.
    Will call any excepthooks that might have been set by other libraries.
    """
    if hasattr(evalue, '_real_tb'):
        tb = evalue._real_tb
        evalue.__traceback__ = tb
    if hasattr(evalue, '__excepthook__'):
        return evalue.__excepthook__(tb)
    return _old_excepthook(etype, evalue, tb)


sys.excepthook = _excepthook


def _make_traceback(depth=0, raise_depth=0):
    """
    Build a reference list of Traceback objects using the call stack.
    The first traceback of the list is associated with the frame at given depth in the call stack.
    """
    try:
        frame = sys._getframe(depth + 1)
    except ValueError:
        err = ValueError("Depth out of range of the call stack.")
        # noinspection PyTypeChecker
        raise AdvancedException.force_depth(err, raise_depth+2) from None
    tbs = [Traceback(None, frame, frame.f_lasti, frame.f_lineno)]

    while 1:
        if not frame.f_back:
            break
        frame = frame.f_back
        tbs.append(Traceback(None, frame, frame.f_lasti, frame.f_lineno))

    tbs = list(reversed(tbs))
    for i in range(len(tbs)):
        try:
            tbs[i].tb_next = tbs[i + 1]
        except IndexError:
            pass

    return tbs[0]


class _AdvancedExceptionMeta(type):
    """
    Metaclass for all advanced exception types.
    """
    def __new__(mcs, name, bases, np, base_error: type[BaseException] = Exception):
        """
        Create and return an advanced exception type, derived from base_error.
        """
        bases_list = list(bases)

        i_special_bases = []
        i = 0
        for b in bases_list:
            if isinstance(b, _AdvancedExceptionMeta):
                i_special_bases.append(i)
            i += 1

        if len(i_special_bases) > 1:
            raise TypeError("Can't inherit from multiple advanced exception types at the same time.")
        if len(i_special_bases) == 0:
            if object in bases_list:
                # noinspection PyUnresolvedReferences
                i_special_bases = [bases_list.index(object)]
                bases_list[bases_list.index(object)] = base_error
            elif base_error not in bases_list:
                i_special_bases = [0]
                bases_list.insert(0, base_error)

        special_base = bases_list[i_special_bases[0]]

        cls = super().__new__(mcs, name, tuple(bases_list), np)
        cls.__exporter__ = cls.__module__
        cls.__module__ = _LIB_NAME if cls.__module__.startswith(_LIB_NAME) else cls.__module__
        cls.__source__ = base_error if not isinstance(special_base, _AdvancedExceptionMeta) else special_base.__source__
        cls._call_args = (name, bases, np)
        if (cls.__source__ not in (Exception, BaseException)) and (name == 'AdvancedException') and (len(bases) == 0):
            cls.__name__ += f"[{cls.__source__.__name__}]"
        return cls

    def __getitem__(cls, item):
        """
        Implement advanced exception type subscription.
        returns an advanced exception type wrapper around item.
        """
        if not isinstance(item, type):
            raise TypeError("AdvancedException[]:", TYPE_ERR_STR.format('type[BaseException]', type(item).__name__)) from None
        if not issubclass(item, BaseException):
            raise TypeError("AdvancedException[]:", TYPE_ERR_STR.format('type[BaseException]', f'type[{item.__base__.__name__}]')) from None

        if cls.__source__ is Exception:
            if issubclass(item, AdvancedException):
                return item
            if item not in _advanced_exc_types:
                # noinspection PyTypeChecker
                _advanced_exc_types[item] = _AdvancedExceptionMeta(*cls._call_args, base_error=item)
            # noinspection PyTypeChecker
            return _advanced_exc_types[item]
        return cls

    def __repr__(cls):
        if (cls.__source__ is not Exception) and (cls._call_args[1] == ()):
            return f"<class '{cls.__qualname__}[{cls.__source__.__qualname__}]'>"
        return super().__repr__()


class AdvancedException(metaclass=_AdvancedExceptionMeta):
    """
    A type that offers advanced control on the traceback displayed to sys.stderr.

    It allows control over the depth in the call stack from which the exception
    is traced, making it possible to remove useless frames from the end of a
    traceback.

    This type also supports exception types that do not derive from it.

    Such types are represented using a template argument, as follows:

    - AdvancedException[TypeError] supports TypeError
    - AdvancedException[ValueError] supports ValueError
    - and so on ...

    If the template argument derives from AdvancedException,
    AdvancedException[template] is template.

    Note:
        AdvancedException[AdvanceException] == AdvancedException
        AdvancedException[type][type2] == AdvancedException[type]
    """
    def __new__(cls, *args, depth=0, **kwargs):
        """
        Create and return a new advanced exception with a traceback, tracked from given depth
        in the call stack, given args and kwargs.
        Zero, the default value for depth, corresponds to the frame from which this class
        is instantiated.
        """
        if not isinstance(depth, int):
            err = TypeError("'depth': " + TYPE_ERR_STR.format('int', type(depth).__name__))
            # noinspection PyTypeChecker
            raise cls.force_depth(err, depth=1)
        if depth < 0:
            # noinspection PyTypeChecker
            raise cls.force_depth(ValueError("Depth cannot be negative."), depth=1)

        tb = _make_traceback(depth=depth+1)
        # noinspection PyArgumentList
        self = cls.__source__.__new__(cls, *args, **kwargs)
        self._real_tb = self.__traceback__ = tb
        self._depth = depth

        _check_sys_excepthook()
        return self

    def __init__(self, *args, **kwargs):
        """
        Only there for parameter consistency.
        """
        if 'depth' in kwargs:
            kwargs.pop('depth')
        # noinspection PyArgumentList
        self.__source__.__init__(self, *args, **kwargs)

    def __excepthook__(self, traceback):
        """
        Customizable hook to the exception's display code.
        This method may be overridden. Default implementation calls an
        equivalent of sys.excepthook(), but not sys.excepthook itself.
        """
        self.__traceback__ = self._real_tb
        # noinspection PyTypeChecker
        return _old_excepthook(self.__class__, self, traceback)

    @classmethod
    def force_depth(cls, error, depth=0, _raise_depth=0):
        """
        Force the traceback of an exception to start from a given depth in the call stack.
        """
        tb = _make_traceback(depth=depth+1, raise_depth=_raise_depth)
        error._real_tb = error.__traceback__ = tb
        if hasattr(error, '_depth'):
            error._depth = depth
        return error

    @property
    def depth(self):
        """
        The depth from which this exception's traceback will be displayed. If set
        to a negative value or one larger than the call stack, ValueError is raised.
        """
        return self._depth

    @depth.setter
    def depth(self, value):
        if value < 0:
            # noinspection PyTypeChecker
            raise self.force_depth(ValueError("depth cannot be negative."), depth=1) from None

        self._real_tb = self.__traceback__ = _make_traceback(value + 1)
        self._depth = value



_advanced_exc_types = {Exception: AdvancedException}


### -------- Advanced Exception types -------- ###

class UnresolvedExternalError(AdvancedException[NameError]):
    """
    Failed to resolve one or more external symbol(s) while loading
    C or C++ code
    """
    pass


class ThreadError(AdvancedException):
    """
    Base class for all thread-related exceptions.
    """
    pass


class ProcessError(AdvancedException[ProcessLookupError]):
    """
    Base class for all process-related exceptions.
    """
    pass


class ProcessModelError(ProcessError):
    """
    The functionality is not supported by process models.
    """
    pass


class ProcessActivityError(ProcessError):
    """
    The functionality is not supported by process activity.
    """
    pass


class UnknownProcessError(ProcessError):
    """
    Unknown process.
    """
    pass


### -------- Helper Functions -------- ###

def _has_instance(iterable_, tp):
    for item in iterable_:
        if isinstance(item, tp):
            return True
    return False


def _count_instances(iterable_, tp):
    n_inst = 0
    for item in iterable_:
        if isinstance(item, tp):
            n_inst += 1

    return n_inst


def _check_sys_excepthook():
    if sys.excepthook != _excepthook:
        _old_excepthook = sys.excepthook
    sys.excepthook = _excepthook

