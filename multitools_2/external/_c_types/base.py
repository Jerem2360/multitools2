import ctypes as _ct
from ctypes import wintypes as _wt

from .._r import GLOBAL_NAME as _GLOBAL_NAME, MODNAME_EXTERNAL as _MODNAME_EXTERNAL, customPath as _customPath
from .._ct_secrets import SimpleCData as _SimpleCData


_HANDLE = "#handle"


@_customPath(_MODNAME_EXTERNAL + '.typedefs')
class CType(type):
    # noinspection PyTypeChecker
    def create_instance(cls, value, *args, **kwargs):
        """
        Create and return an instance of a C type.
        Either pass in a value that will be passed to the C type's C base constructor,
        or pass in a handle to the C instance directly.
        Other arguments are passed in, if any, to the base class constructor.
        """
        base: type[cls.__base__] = cls.__base__

        if isinstance(value, _SimpleCData):
            if not isinstance(value, cls.__c_base__):
                raise TypeError(f"Passed a reference to C data of the wrong type.")

            instance = base.__new__(cls, value.value, *args, **kwargs)
            base.__setattr__(instance, _HANDLE, value)
            return instance

        instance = base.__new__(cls, value, *args, **kwargs)
        base.__setattr__(instance, _HANDLE, cls.__c_base__(value))
        return instance

    def __new__(mcs, name, bases, np):
        """
        Create and return a new C type.
        """
        # setup handle property for class:
        np['__handle__'] = property(lambda self: getattr(self, _HANDLE))

        # look for the specified C base in ctypes:
        if 'base' in np:
            base_s = np['base'].replace(' ', '').replace('unsigned', 'u')
            if not hasattr(_ct, 'c_' + base_s):

                if not hasattr(_wt, np["base"]):
                    raise ValueError(f"'{base_s}' is not a valid C base.")
                np['__c_base__'] = getattr(_wt, base_s)

            np['__c_base__'] = getattr(_ct, 'c_' + base_s)
        else:
            raise TypeError(f"C type '{name}' must define a C base.")

        # calculate the size of the type:
        np['__size__'] = _ct.sizeof(np['__c_base__'])

        # default value for to_c() method:
        if not (('to_c' in np) and callable(np['to_c'])):
            def _to_c(self):
                return self.__handle__

            np['to_c'] = _to_c

        # default value for from_c() class method:
        if not (('from_c' in np) and isinstance(np['from_c'], classmethod)):
            def _from_c(_cls, cvalue):
                return _cls.create_instance(cvalue)

            np['from_c'] = classmethod(_from_c)

        # default value for __new__() method:
        if not (('__new__' in np) and callable(np['__new__'])):
            def __new__(_cls, *args, **kwargs):
                return _cls.create_instance(*args, **kwargs)

            np['__new__'] = __new__

        # default value for raw() method:
        if not (('raw' in np) and callable(np['raw'])):
            def _raw(self):
                return self.__handle__.value

            np['raw'] = _raw

        # create type:
        cls = super().__new__(mcs, name, bases, np)

        # set module of type:
        cls.__module__ = f"{_GLOBAL_NAME}.external.typedefs"

        return cls

    def __class_getitem__(mcs, item):
        return type[item]

