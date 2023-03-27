import types


class Interface_Type(type):
    def __new__(mcs, name, bases, np):
        requirements = []

        for name in np:
            if name in ('__module__', '__qualname__'):
                continue
            requirements.append(name)

        cls = type.__new__(mcs, name, bases, np)
        cls.__requirements__ = requirements
        return cls

    # noinspection PyMethodMayBeStatic
    def __check__(cls, tp):
        return NotImplemented

    def __check_instance__(cls, instance):
        return cls.__check__(type(instance))

    def __instancecheck__(cls, instance):
        # print(t_instance, instance)
        from ._typeshed import MethodWrapper
        tp = type(instance)
        impl = cls.__check_instance__(instance)
        if impl is NotImplemented:
            impl = True
            for req in cls.__requirements__:
                if not hasattr(tp, req):
                    impl = False
                    break
                attr = getattr(instance, req)
                if isinstance(attr, (types.FunctionType, types.MethodType, MethodWrapper)):
                    return True

                if not isinstance(attr, type(getattr(cls, req))):
                    impl = False
                    break
        return impl

    def __subclasscheck__(cls, subclass):
        impl = cls.__check__(subclass)
        if impl is NotImplemented:
            impl = True

            for req in cls.__requirements__:
                if not hasattr(subclass, req):
                    impl = False
                    break
                if not isinstance(getattr(subclass, req), type(getattr(cls, req))):
                    impl = False
                    break
        return impl


class Interface(metaclass=Interface_Type):
    @classmethod
    def __check__(cls, tp):
        return NotImplemented

    @classmethod
    def __check_instance__(cls, instance):
        return cls.__check__(type(instance))


class Buffer(Interface):
    @classmethod
    def __check_instance__(cls, instance):
        import ctypes
        return bool(ctypes.pythonapi.PyObject_CheckBuffer(ctypes.py_object(instance)))

    @classmethod
    def __check__(cls, tp):
        raise TypeError("Cannot check for buffer types.")


class SupportsInt(Interface):
    def __int__(self): ...


class SupportsFloat(Interface):
    def __float__(self): ...


class SupportsBool(Interface):
    def __bool__(self): ...


class SupportsBytes(Interface):
    def __bytes__(self): ...


class SupportsGetItem(Interface):
    def __getitem__(self, item): ...


class SupportsSetItem(Interface):
    def __setitem__(self, key, value): ...


class SupportsDelItem(Interface):
    def __delitem__(self, key): ...


class SupportsIndex(Interface):
    def __index__(self): ...


class SupportsLen(Interface):
    def __len__(self): ...


class Iterable(Interface):
    def __iter__(self): ...


class Iterator(Interface):
    def __next__(self): ...


class AsyncIterable(Interface):
    def __aiter__(self): ...


class AsyncIterator(Interface):
    def __anext__(self): ...


class Awaitable(Interface):
    def __await__(self): ...

