from ._metacls import MultiMeta
from .. import _hidden_builtins
from . import _field


__all__ = [
    'MultiMeta',
    'abstract',
    'static',
]


def abstract(*args, **kwargs):
    """
    possible calls:

    - @abstract(static=False) -> Abstract method
    def f(): ...

    - size = abstract(10, static=False) -> Abstract Attribute

    - @abstract -> Abstract Method
    def f(): ...

    Set the attribute of a multitools class as abstract. Support for static
    combination.
    Keyword arguments are all optional.

    Abstract attributes require subclasses to override them.
    """
    _static = kwargs.get('static', False)
    if len(args) == 0:

        def _inner(item):
            res = _field.FieldWrapper(item)
            res.__abstract__ = True
            if _static:
                res.__static__ = True
            return res
        return _inner
    item = args[0]
    res = _field.FieldWrapper(item)
    res.__abstract__ = True
    if _static:
        res.__static__ = True
    return res


def static(item):
    """
    possible calls:

    - @static -> Static Method
    def f(): ...

    - size = static(10) -> Static Attribute

    Sets specified or decorated object as a static attribute of it's container class.
    Static attributes don't depend on an instance, but only on their container class.
    """
    res = _field.FieldWrapper(item)
    res.__static__ = True
    return res


