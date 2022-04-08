import _thread
import ctypes

from .._ref import *


class Thread(metaclass=MultiMeta):
    __fields__ = [

    ]

    def __init__(self, function=None):
        if function is None:
            temp_func = self.main if (hasattr(self, 'main') and callable(self.main)) else lambda self, *a, **k: None
        elif callable(function):
            temp_func = function
        else:
            raise TypeError(TYPE_ERROR_STR.format('function', '(Any, ...) -> Any', type(function).__name__))

        def _real_func(*a, **kw):
            try:
                temp_func(*a, **kw)
            except KeyboardInterrupt:
                pass

        self._function = _real_func

    @callback
    def __call__(self, *args, **kwargs):
        result = self
        result._handle = _thread.start_new_thread(self._function, *args, kwargs=kwargs)
        return result
