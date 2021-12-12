from dataclasses import dataclass as _dataclass


_MultiMeta_Supported = {
    "__name__": "name",
    "__bases__": "bases",
    "__base__": "main_base",
    "__origin_dict__": "original_dict",
}


# noinspection PyUnresolvedReferences
def getattr_root(tp, name):
    if not isinstance(tp, type):
        raise TypeError("tp")
    if not hasattr(tp, "__class_data__"):
        raise TypeError(tp.__name__)
    if not isinstance(name, str):
        raise TypeError("value")

    return tp >> name


# noinspection PyUnresolvedReferences
def setattr_root(tp, name, value):
    if not isinstance(tp, type):
        raise TypeError("tp")
    if not hasattr(tp, "__class_data__"):
        raise TypeError(tp.__name__)
    if not isinstance(name, str):
        raise TypeError("value")

    return tp << (name, value)


@_dataclass
class _ClassData:
    name: str
    bases: tuple[type]
    original_dict: dict
    main_base: type
    is_abstract: bool

    def __repr__(self):
        return f"<properties descriptor of class '{self.name}'>"


class AbstractMethodDescriptor:

    def __init__(self, func):
        self._func = func
        self._overridden = False
        try:
            self.__name__ = self._func.__name__
            self.__qualname__ = self._func.__qualname__
        except AttributeError:
            pass

    # noinspection PyUnresolvedReferences
    def __call__(self, *args, **kwargs):
        if not self._overridden:
            raise ValueError(f"Abstract method '{self._func.__name__}' missing override.")
        return self._func(*args, **kwargs)

    def override(self, value):
        self._func = value
        self._overridden = True
        return value

    @property
    def overridden(self):
        return self._overridden

    @property
    def __annotations__(self):
        return self._func.__annotations__ if hasattr(self._func, "__annotations__") else {}

    @property
    def __code__(self):
        return self._func.__code__ if hasattr(self._func, "__code__") else None

    @property
    def __closure__(self):
        return self._func.__closure__ if hasattr(self._func, "__closure__") else ()

    @property
    def __defaults__(self):
        return self._func.__defaults__ if hasattr(self._func, "__defaults__") else ()

    @property
    def __globals__(self):
        return self._func.__globals__ if hasattr(self._func, "__globals__") else {}

    @property
    def __kwdefaults__(self):
        return self._func.__kwdefaults__ if hasattr(self._func, "__kwdefaults__") else {}


class MultiMeta(type):
    def __init__(cls, name, bases, dct):
        # print(dct)
        class_name = name
        class_main_base = bases[0] if len(bases) > 0 else object
        cls << ("__abstractmethods__", {})

        class_orig_dict = {
            '__module__': dct['__module__'],
            '__qualname__': dct['__qualname__'],
        }
        class_is_abstract = False
        for attrname, attr_ in dct.items():
            if isinstance(attr_, AbstractMethodDescriptor):
                # we need to know if the class is abstract:
                class_is_abstract = True

                # if class is abstract, block the __init__ method:
                def __init__(self, *args, **kwargs):
                    raise ValueError(f"Class '{(cls >> '__class_data__').name}' is abstract.")

                cls << ["__init__", __init__]

        # list of attributes coming from the class' bases:
        _bases_dict = {}
        for bs in bases:
            for attr_nm, attr_ in bs.__dict__.items():
                _bases_dict[attr_nm] = attr_

        # if an attribute is an abstract method and it was overridden, create override:
        for base_attr_name, base_attr in _bases_dict.items():
            # print(base_attr)
            if isinstance(base_attr, AbstractMethodDescriptor):
                if base_attr_name in dct:
                    base_attr.override(dct[base_attr_name])

                elif not class_is_abstract:
                    raise ValueError(f"Abstract method '{base_attr.__name__}' missing override.")

            dct[base_attr_name] = base_attr

        for attr in dct:
            class_orig_dict[attr] = dct[attr]

        class_bases = bases if len(bases) > 0 else (object,)
        cls << ("__class_data__", _ClassData(class_name, class_bases, class_orig_dict, class_main_base, class_is_abstract))

        super().__init__(name, bases, dct)

    def __getattr__(cls, item, _root=False, **kwargs):
        if _root:
            return super().__getattribute__(item)

        if item in _MultiMeta_Supported:
            return getattr((cls >> "__class_data__"), _MultiMeta_Supported[item])
        return super().__getattribute__(item)

    def __rshift__(cls, other: str):
        return cls.__getattr__(other, _root=True)

    def __lshift__(cls, other: tuple):
        return setattr(cls, other[0], other[1])

    def __repr__(cls):
        return f"<multitools class '{(cls >> '__class_data__').name}'>"

