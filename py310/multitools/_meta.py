from dataclasses import dataclass
from typing import Any


class AbstractMethodDescriptor:
    """
    The type of data that is stored inside and abstract class
    about it's abstract methods.
    See 'MultiMeta' for more info.
    """
    def __init__(self, function):
        """
        Create a new abstract method descriptor, that
        provides access to every default attribute of a
        normal function.
        Accepts any callable.
        """
        if not callable(function):
            raise TypeError(f"'function': Expected type 'Callable[[Any, ...], Any]', got '{type(function).__name__}' instead.")

        # make sure the decorated function doesn't declare a body:
        if hasattr(function, "__code__"):
            match function.__code__.co_code:
                case b"d\x01S\x00":  # binary code where there is documentation but function does nothing
                    pass
                case b"d\x00S\x00":  # same, but no documentation
                    pass
                case _:  # function does something: it declared a body
                    raise ValueError("abstract methods must not declare a body.")
        self._function = function
        self._is_overridden = False

        # set __name__ and __qualname__ as if we were the function itself:
        try:
            self.__name__ = self._function.__name__
            self.__qualname__ = self._function.__qualname__
            self.__doc__ = self._function.__doc__
        except AttributeError:  # to support callables other than functions, since they may not have __name__ and __qualname__
            pass

    def __call__(self, *args, **kwargs):
        """
        If the abstract method is overridden, call self with normal arguments.
        Otherwise, raise ValueError.
        """
        if not self._is_overridden:
            if not hasattr(self, "__qualname__"):
                raise ValueError("Abstract callable missing override.")
            raise ValueError(f"Abstract Method '{self.__qualname__}' missing override.")
        return self._function(*args, **kwargs)

    def override(self, new_function):
        """
        Override self.

        Overriding an abstract method gives it the ability to be called. When done,
        it accepts any callable, and passed-in functions may declare a body.
        """
        if not callable(new_function):
            raise TypeError(f"'new_function': Expected type 'Callable[[Any, ...], Any]', got '{type(new_function).__name__}' instead.")

        # here, the override can declare a body, no need to check for it.

        # same as in __init__, but mark as overridden:
        if new_function.__doc__ != "":
            self.__doc__ = new_function.__doc__
        self._function = new_function
        self._is_overridden = True

        try:
            self.__name__ = self._function.__name__
            self.__qualname__ = self._function.__qualname__

        except AttributeError:
            del self.__name__
            del self.__qualname__

    def __repr__(self):
        """
        Implement repr(self)
        """
        return f"<abstractmethod descriptor at {str(hex(id(self)))}, overridden={self._is_overridden}>"

    overridden = property(lambda self: self._is_overridden)
    # declare all normal function attributes as properties, except __name__ and __qualname__, for compatibility issues:
    __annotations__ = property(lambda self: self._function.__annotations__ if hasattr(self._function, "__annotations__") else {})
    __code__ = property(lambda self: self._function.__code__ if hasattr(self._function, "__code__") else None)
    __closure__ = property(lambda self: self._function.__closure__ if hasattr(self._function, "__closure__") else ())
    __defaults__ = property(lambda self: self._function.__defaults__ if hasattr(self._function, "__defaults__") else ())
    __globals__ = property(lambda self: self._function.__globals__ if hasattr(self._function, "__globals__") else {})
    __kwdefaults__ = property(lambda self: self._function.__kwdefaults__ if hasattr(self._function, "__kwdefaults__") else {})


@dataclass
class ClassData:
    name: str
    bases: tuple[type]
    abstract: bool
    cls_dict: dict[str, Any]
    superclass: type

    def __repr__(self):
        return f"<data descriptor of class '{self.name}'>"


# noinspection PyArgumentList,PyTypeChecker
class MultiMeta(type):
    """
    **internal only**
    A metaclass offering various advantages.

    Changes::
    - access to abstract method functionality
    - all attributes inherited from parent classes are directly copied to the class __dict__

    Abstract method functionality::

    An abstract method is a method of a class that has to
    be overridden by any child class. If a class defines at
    least one abstract method, it is called an abstract class.

    Since an abstract class' abstract methods need to be overridden
    by any child class, it cannot be instantiated. In this case,
    the instantiation of the class will raise a ValueError.

    If a class is found to not override a parents abstract
    method, a ValueError is raised. Abstract methods must
    not declare a body, otherwise, a ValueError is also raised.
    """
    def __init__(cls, name, bases, dct):
        """
        Create a new class and manage attributes.
        Copy attributes from parent classes while managing whether the class
        is abstract or not. Also manage abstract methods and their overriding.
        """
        cls_name = name
        cls_bases = bases if len(bases) > 0 else (object,)
        cls_super = bases[0] if len(bases) > 0 else object
        cls_is_abstract = False
        cls_dict = dct
        bases_dict = {}

        # merge all dictionaries from the class bases:
        for base in bases:
            bases_dict = {**bases_dict, **base.__dict__}

        # resolve abstract methods:
        for key, item in cls_dict.items():
            if key in bases_dict:
                if isinstance(bases_dict[key], AbstractMethodDescriptor):
                    temp = bases_dict[key]
                    temp.override(item)
                    cls_dict[key] = temp
            else:
                if isinstance(item, AbstractMethodDescriptor):
                    cls_is_abstract = True

        # merge bases dictionaries with actual class dictionary:
        for key, item in bases_dict.items():
            if key not in cls_dict:
                if isinstance(item, AbstractMethodDescriptor):
                    if not cls_is_abstract:
                        raise ValueError(f"Abstract method '{key}' missing override.")
                cls_dict[key] = item

        # store the data & type.__init__():
        cls.__data__ = ClassData(cls_name, cls_bases, cls_is_abstract, cls_dict, cls_super)
        super().__init__(cls_name, cls_bases, cls_dict)
        # if class is abstract, forbid usage of __init__, using a wrapper:
        if cls_is_abstract:
            old_init: Any = cls.__init__

            # we don't wrap __new__ so that support for pickling is kept.
            # wrap __init__ into following function:
            def __init__(self: object, *args, **kwargs):
                if type(self) == cls:  # if instance comes from the class itself, excluding child classes, forbid instantiation
                    raise ValueError(f"Class '{cls.__data__.name}' is abstract so it cannot be instantiated.")
                old_init(self, *args, **kwargs)  # otherwise, execute __init__ as usual

            cls.__init__: Any = __init__

    def __repr__(cls):
        """
        Implement repr(self)
        """
        return f"<multitools class '{cls.__data__.name}'>"

    def __getitem__(cls, item):
        return cls

