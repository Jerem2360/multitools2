from ._metacls import MultiMeta
from ._dec import abstract, static, callback, Decorator


"""
Private subpackage for custom attribute management.
Every class in multitools have MultiMeta as metaclass.
"""


__all__ = [
    'MultiMeta',
    'abstract',
    'static',
    'callback',
    'Decorator',
]

