from .. import _meta
from .. import _tools


Decorator = _tools.Decorator


@Decorator
def generic(cls, *types):
    """
    Allow a type to be generic and support template arguments,
    a bit like for typing.Generic. The main difference is that
    template arguments are runtime type-checked towards the
    decorator's arguments, which must be types. Template arguments
    can also be implemented by defining a __template__ class method
    that takes the template arguments as parameters.
    If no arguments are passed, this decorator does nothing.

    For example:

    @generic(type1, type2, ...)
    class C(metaclass=MultiMeta):
        def __template__(t_instance, arg1: type1, arg2: type2, ...):
            res = t_instance.copy(t_instance)
            # do stuff
            return res

    C[arg1, arg2, ...] -> generic 'C' with arguments arg1, arg2, ...

    Note that template types are cached, so __template__ will
    be called only once for each distinct set of template arguments.
    """
    return _meta.generic(*types)(cls)


def abstractmethod(fn):
    """
    Make a method abstract.
    """
    return _meta.abstractmethod(fn)

