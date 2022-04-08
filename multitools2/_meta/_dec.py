from ._const import *
from ._locals import *
from ._metacls import *

#----- Avoid using MultiMeta since there is an infinite recursion risk -----#


class Decorator(metaclass=MultiType):
    """
    The type of every decorator in multitools.
    """
    def __init__(self, func):
        self._func = func

    def __call__(self, *args, **kwargs):
        if len(args) == 0:
            def temp(func):
                return self._func(func)
            return temp
        if len(args) == 1 and is_function(args[0]):
            return self._func(args[0])

        def temp(func):
            return self._func(func, *args, **kwargs)
        return temp

    def __getattr__(self, item):
        if (item == CALL) or (item == INIT):
            return super().__getattribute__(item)
        return getattr(self._func, item)


@Decorator
def abstract(ob, static=False):
    """
    Make a method or class abstract.
    This means that any child class should override this method. This also disables
    instantiation of the class or the method's owner class.
    """
    if isinstance(ob, MultiMeta):
        mt = MultiMeta(ob, decorations=[DEC_ABSTRACT])
        return mt

    field = Field(staticmethod(ob) if static else ob)
    setattr(field, DEC_ABSTRACT, True)
    if static:
        setattr(field, DEC_STATIC, True)
    return field


@Decorator
def static(func):
    """
    Make a method static.
    This means the method neither depends on its container class nor on its corresponding instance.
    """
    field = Field(staticmethod(func))
    setattr(field, DEC_STATIC, True)
    return field


@Decorator
def callback(func, static=False, abstract=False):
    """
    Define a method as callback method.
    This means it will be able to support any external callback, as opposed to
    default multitools methods.
    """
    field = Field(staticmethod(func) if static else func)
    setattr(field, DEC_CALLBACK, True)
    if static:
        setattr(field, DEC_STATIC, True)
    if abstract:
        setattr(field, DEC_ABSTRACT, True)
    return field


