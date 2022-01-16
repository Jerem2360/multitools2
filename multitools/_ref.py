from ._meta import *
from ._type_check import typecheck


def reference(target_name, default, writable=True):
    """
    A reference to another attribute of the current instance.

    Will act as an instance attribute or a class attribute
    depending on the context. Custom getters and setters are
    triggered properly.

    In case it fails, return default.
    """
    typecheck(target_name, (str,), target_name="target_name")

    # make sure we can inherit from type(default):
    base = type(default)
    try:
        class test(base):
            pass
    except TypeError:
        # if not, we will inherit from plain object:
        base = object

    # create the true 'reference' class as in the stub, with dynamic inheritance:

    # noinspection PyShadowingNames
    class reference(base, metaclass=MultiMeta):
        def __init__(self):
            """
            Initialize a new reference object with given target and default return value
            """
            self._target = target_name
            self._default = default
            self._writable = writable

        def __get__(self, instance, owner):
            """
            Implement instance.self or owner.self
            """
            if instance is None:
                try:
                    res = self._get_target(owner)
                    typecheck(res, (type(self._default),), target_name="default",
                              expected_type_name=type(res).__name__)
                    return res
                except AttributeError:
                    return self._default
            try:
                res = self._get_target(instance)
                typecheck(res, (type(self._default),), target_name="default",
                          expected_type_name=type(res).__name__)
                return res
            except AttributeError:
                return self._default

        def _get_target(self, obj):
            """
            Internal method for reading dotted format
            and referencing the right attribute.
            """
            name = self._target
            if ('.' in name) and len(name.split('.')) == 2:
                path = name.split('.')
                owner = getattr(obj, path[0])
                result = getattr(owner, path[1])
                return result
            return getattr(obj, name)

        def _set_target(self, obj, value):
            """
            Internal method for reading dotted format of name
            and assigning the right attribute to value.
            """
            name = self._target
            if ('.' in name) and len(name.split('.')) == 2:
                path = name.split('.')
                temp = getattr(obj, path[0])
                setattr(temp, path[1], value)
                setattr(obj, path[0], temp)
                return
            setattr(obj, name, value)

        def __set__(self, instance, value):
            """
            Implement instance.self = value
            """
            if self._writable:
                try:
                    self._set_target(instance, value)
                except AttributeError:
                    pass
                return
            raise AttributeError("Read-only attribute.")

        def __repr__(self):
            """
            Implement repr(self)
            """
            return f"<reference on '{self._target}' attribute at {str(hex(id(self)))}>"

    return reference()

