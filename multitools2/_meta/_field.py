from .. import _misc


class FieldWrapper(metaclass=_misc.SimpleMeta):

    __abstract__ = False
    __static__ = None
    is_function = False
    _staticmethod = False
    _classmethod = False

    def __init__(self, value):
        if isinstance(value, FieldWrapper):
            raise TypeError("Fields cannot contain 'FieldWrapper' objects.")
        if isinstance(value, classmethod):
            self._value = value.__func__
            self._classmethod = True
        elif isinstance(value, staticmethod):
            self._value = value.__func__
            self._staticmethod = True

        self._value = value
        if callable(self._value):
            self.is_function = True

    @property
    def value(self):
        if self._staticmethod:
            return staticmethod(self._value)
        if self._classmethod:
            return classmethod(self._value)
        return self._value

