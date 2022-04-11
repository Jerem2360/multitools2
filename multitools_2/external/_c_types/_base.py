import ctypes as _ct


from .._r import GLOBAL_NAME as _GLOBAL_NAME, MODNAME_EXTERNAL as _MODNAME_EXTERNAL, customPath as _customPath


@_customPath(_MODNAME_EXTERNAL + '.typedefs')
class CType(type):

    def __new__(mcs, name, bases, np):
        if 'base' in np:
            base_s = np['base'].replace(' ', '')
            if not hasattr(_ct, 'c_' + base_s):
                raise ValueError(f"'{base_s}' is not a valid C base.")
            np['__c_base__'] = getattr(_ct, 'c_' + base_s)
        else:
            raise TypeError(f"C type '{name}' must define a C base.")

        np['__size__'] = _ct.sizeof(np['__c_base__'])

        if not (('to_c' in np) and callable(np['to_c'])):
            def _to_c(self):
                return np['__c_base__'](self)

            np['to_c'] = _to_c

        if not (('from_c' in np) and isinstance(np['from_c'], classmethod)):
            def _from_c(cls, cvalue):
                return cls(cvalue.value)

            np['from_c'] = classmethod(_from_c)

        cls = super().__new__(mcs, name, bases, np)

        cls.__module__ = f"{_GLOBAL_NAME}.external.typedefs"
        return cls

    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __class_getitem__(mcs, item):
        return type[item]

