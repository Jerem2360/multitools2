from dataclasses import dataclass
from . import _misc


class instance:
    def __init__(self, value):
        self.value = value


class FieldWrapper(metaclass=_misc.SimpleMeta):

    __abstract__ = False
    __static__ = False
    is_function = False

    def __init__(self, value):
        if isinstance(value, FieldWrapper):
            raise TypeError("Fields cannot contain 'FieldWrapper' objects.")
        self._value = value
        if callable(self._value):
            self.is_function = True

    value = property(lambda self: self._value)


class MultiSuper(metaclass=_misc.SimpleMeta):
    def __init__(self, __self__):
        self.__self__ = __self__

    def __getattr__(self, item):
        cls = type(self.__self__)
        mro = list(cls.__mro__)
        mro.pop(0)
        for subclass in mro:
            if hasattr(subclass, item):
                res = getattr(subclass, item)
                if isinstance(res, FieldWrapper):
                    return res.value
                return res

        if not hasattr(cls, item):
            raise AttributeError(item)
        res = getattr(cls, item)
        if isinstance(res, FieldWrapper):
            return res.value
        return res

    def __repr__(self):
        return f"<reference to class '{self.__getattr__('__name__')}' at {hex(id(self))}>"


@dataclass
class ClsData(metaclass=_misc.SimpleMeta):
    """
    Internal data structure for storing info about multitools classes
    """
    name: str
    abstract: bool
    field_defs: tuple
    static_fields: dict[str, FieldWrapper]
    instance_fields: dict[str, FieldWrapper]


def _type_hasattr(obj, name):
    if isinstance(obj, MultiMeta):
        return name in obj.__data__.static_fields
    return hasattr(obj, name)


# noinspection PyPropertyDefinition
class MultiMeta(type):
    """
    Multitools types are different to builtin type instances.
    The only internal callback attribute they have is the __data__ class attribute.
    This static field contains all the useful data about the class, including it's other fields.
    This allows to store class attributes and instance attribute definitions separately in the class,
    respectively in '__data__.static_fields' and '__data__.instance_fields'.
    Those work exactly as the '__dict__' field of a normal type object.

    Since normal type objects don't differentiate between class attributes and instance attribute definitions,
    a specific way of doing this on class declaration is needed.
    When declaring MultiMeta as the metaclass of a class, a special attribute '__fields__' can be declared to
    list all the field names instances of the class should have. When declaring a variable inside the class,
    if it's name is listed into '__fields__' it will count as an instance attribute, otherwise, it will count as
    a static class attribute.
    Any name in '__fields__' that aren't declared inside the class will count as an instance attribute who's
    value defaults to None.
    An attribute of a Multitools type or of it's instances is considered abstract if they have an '__abstract__'
    attribute or field set to True.
    """

    # noinspection PyDefaultArgument
    def __new__(mcs, arg1, bases=(), dct={}, abstract=False):
        """
        Create a new multitools type either from an existing one or from scratch.
        """

        # type checking:
        if not isinstance(abstract, bool):
            raise TypeError(f"'abstract': Expected type 'bool', got '{type(abstract).__name__}' instead.")

        # creation from an existing one:
        if isinstance(arg1, MultiMeta):

            # make sure 'bases' and 'dct' are not set:
            if (bases != ()) or (dct != {}):
                raise ValueError(f"If 'source' is set, 'bases' and 'dct' must not be set.")

            # update the 'abstract' parameter of the class:
            cls_data = type.__getattribute__(arg1, "#data")
            cls_data.abstract = abstract
            type.__setattr__(arg1, "#data", cls_data)
            return arg1

        # type checking:
        if not isinstance(arg1, str):
            raise TypeError(f"'name': Expected type 'str', got '{type(arg1).__name__}' instead.")
        if not isinstance(bases, tuple):
            raise TypeError(f"'bases': Expected type 'tuple', got '{type(bases).__name__}' instead.")
        if not isinstance(dct, dict):
            raise TypeError(f"'dct': Expected type 'dict', got '{type(dct).__name__}' instead.")

        # get correct value for __doc__:
        try:
            doc = dct['__doc__']
        except KeyError:
            doc = None

        if '__fields__' not in dct:
            dct['__fields__'] = []

        # the __dict__ attribute of the new class:
        # noinspection PyArgumentList
        new_dict = {
            "#data": ClsData(arg1, abstract, list(dct['__fields__']), {}, {}),
            "__doc__": doc,
        }

        # if needed, propagate __classcell__ to the new class:
        if '__classcell__' in dct:
            new_dict['__classcell__'] = dct['__classcell__']

        # create meta-instance (class):
        cls = super().__new__(mcs, arg1, bases, new_dict)

        # store attributes into class data instead of __dict__.
        cls_data = type.__getattribute__(cls, "#data")
        for k, v in dct.items():
            if isinstance(v, FieldWrapper):
                field = v
            else:
                field = FieldWrapper(v)

            field.__static__ = not bool(('__fields__' in dct) and (k in dct['__fields__']))
            if field.__abstract__ and not cls_data.abstract:
                cls_data.abstract = True
            setattr(cls, k, field)
        type.__setattr__(cls, "#data", cls_data)

        # store attributes coming from the base classes into a temporary buffer:
        bases_static = {}
        bases_instance = {}
        for base in reversed(bases):
            if isinstance(base, MultiMeta):
                bases_static = {**bases_static, **base.__data__.static_fields}
                bases_instance = {**bases_instance, **base.__data__.instance_fields}
                continue
            bases_static = {**bases_static, **base.__dict__}
            bases_instance = {**bases_instance, **base.__dict__}

        # then treat each of the static attributes:
        for sk, sv in bases_static.items():
            if sk not in cls.__data__.static_fields:
                if isinstance(sv, FieldWrapper):
                    field = sv
                else:
                    field = FieldWrapper(sv)
                if field.__abstract__ or (hasattr(sv, '__abstract__') and sv.__abstract__):
                    ftype = "Abstract method" if field.is_function else "Abstract field"
                    err = TypeError if field.is_function else AttributeError
                    raise err(f"{ftype} '{sk}' missing override")

        # and each of the instance attributes:
        for ik, iv in bases_instance.items():
            if ik not in cls.__data__.instance_fields:
                if hasattr(iv, '__abstract__') and iv.__abstract__:
                    if callable(cls.__data__.instance_fields[ik]):
                        raise TypeError(f"Inherited abstract instance method '{ik}' missing override.")
                    raise AttributeError(f"Inherited abstract instance attribute '{ik}' missing override.")
                field = FieldWrapper(iv)
                field.__static__ = False
                setattr(cls, ik, field)

        # make sure cls has a '__fields__' attribute of the right type (tuple or list):
        if not hasattr(cls, '__fields__'):
            cls.__fields__ = []
        if not isinstance(cls.__fields__, (list, tuple)):
            raise TypeError(f"'__fields__': Expected type Union[tuple, list], got '{type(cls.__fields__).__name__}' instead.")

        # return the actual meta-instance:
        return cls

    # noinspection PyDefaultArgument,PyArgumentList
    def __init__(cls, *args, **kwargs):
        """
        Initialize a new class either from an existing one or from scratch.
        """
        if len(args) != 3:
            return
        base = cls.__bases__[0]

        def _init(self, *a, **kw):
            if base is object:
                base.__init__(self)
            else:
                base.__init__(self, *a, **kw)

        # noinspection PyArgumentList
        def _new(c, *a, **kw):
            if base is object:
                return base.__new__(c)
            return base.__new__(c, *a, **kw)

        custom_init = cls.__data__.static_fields['__init__'].value if '__init__' in cls.__data__.static_fields else \
            _init
        custom_new = cls.__data__.static_fields['__new__'].value if '__new__' in cls.__data__.static_fields else \
            _new

        def true_init(self, *a, **kw):
            # print("init", self, a, kw)
            return custom_init(self, *a, **kw)

        def true_new(clas, *a, **kw):
            # print("new", clas, a, kw)
            field_defs = clas.__data__.field_defs
            self = custom_new(clas, *a, **kw)
            for field_name in field_defs:
                if field_name in clas.instance_attrs:
                    setattr(self, field_name, clas.instance_attrs[field_name].value)
                    continue
                setattr(self, field_name, None)
            return self

        type.__init__(cls, *args, **kwargs)

        cls.__builtin_setattr__('__init__', true_init)
        # noinspection PyTypeChecker
        cls.__init__ = true_init

        cls.__builtin_setattr__('__new__', true_new)
        cls.__new__ = true_new

    def __setattr__(cls, key, value):
        """
        Implement cls.key = value
        """

        # make the FieldWrapper object & detect if it's static or not:
        is_instance_field = False
        if isinstance(value, FieldWrapper):
            to_set = value
            if not value.__static__:
                is_instance_field = True
        elif isinstance(value, instance):
            is_instance_field = True
            to_set = FieldWrapper(value.value)
        else:
            to_set = FieldWrapper(value)

        # get the class '__data__' attribute:
        cls_data = type.__getattribute__(cls, "#data")

        # set field:
        if is_instance_field:
            cls_data.instance_fields[key] = to_set
        else:
            cls_data.static_fields[key] = to_set

        # update '__data__':
        return type.__setattr__(cls, "#data", cls_data)

    def __getattr__(cls, item):
        """
        Implement cls.key
        Search only static attributes.
        """
        # get the class '__data__' attribute:
        cls_data = type.__getattribute__(cls, "#data")
        try:
            # get the wrapper of the static field:
            result = cls_data.static_fields[item]
            # extract and return the field value:
            return result.value
        except KeyError as e:  # if field not found in '__data__'
            try:
                return type.__getattribute__(cls, item)  # use __dict__ attribute
            except AttributeError:
                raise AttributeError(*[repr(arg) for arg in e.args])  # re-raise the initial error

    def __builtin_setattr__(cls, name, value):
        """
        Set a value of the __dict__ of the class. This has not
        many uses.
        """
        return type.__setattr__(cls, name, value)

    def __builtin_getattr__(cls, name):
        """
        Get a value from the __dict__ of the class. This has not
        many uses.
        """
        return type.__getattribute__(cls, name)

    def __super__(cls):
        """
        Get the owner's superclass. Replicates the behaviour
        of super() but from outside or inside an instance.
        """
        # type.__mro__ contains the order in which attributes override each other in base classes.
        return MultiSuper(cls)

    def __repr__(cls):
        """
        Implement repr(cls)
        """
        name = type.__getattribute__(cls, "#data").name
        return f"<multitools class '{name}'>"

    def __call__(cls, *args, **kwargs):
        if cls.__data__.abstract:
            raise TypeError(f"Cannot instantiate abstract class '{cls.__data__.name}'.")
        new_method = getattr(cls, '__new__')
        self = new_method(cls, *args, **kwargs)
        init_method = getattr(cls, '__init__')
        init_method(self, *args, **kwargs)
        return self

    instance_attrs = property(lambda cls: _misc.GetSetDict(cls.__data__.instance_fields))
    """Opens instance attributes to a read-only view from the outside."""
    __data__ = property(lambda cls: cls.__builtin_getattr__("#data"))
    """Where everything about the class is stored."""

