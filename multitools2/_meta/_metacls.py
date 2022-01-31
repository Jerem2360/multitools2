from . import _data
from . import _field

from .. import _hidden_builtins


DATA = "#data"
DICT_VALID = ('__dict__', '__init__', '__new__', '__module__', '__qualname__')


def _is_iter(obj):
    return hasattr(obj, '__iter__')


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
    @staticmethod
    def __get_mro(cls, bases):
        result = [cls]
        for base in bases:
            if base not in result:
                result.append(base)
        for base in bases:
            try:
                mro = base.__mro__
            except AttributeError:
                mro = ()
            for entry in mro:
                if entry not in result:
                    result.append(entry)
        return result

    @staticmethod
    def __sort_static_instance(np, field_defs, **kwargs):
        """
        Internal helper method for sorting variables in class definition.
        """
        np_res_s = {}
        np_res_i = {}
        abstract = kwargs.get('abstract', False)

        # treat each variable in class definition:
        for npk, npv in np.items():

            # make the value a field if it is not already the case:
            field = npv if isinstance(npv, _field.FieldWrapper) else _field.FieldWrapper(npv)

            # if static is set to be default:
            if field.__static__ is None:
                if isinstance(field.value, _hidden_builtins.FunctionType):
                    field.__static__ = False  # a method must be an instance attribute by default
                else:
                    field.__static__ = not bool(npk in field_defs)  # a variable must be a static attribute by default

            # if an abstract field is found, make the entire class abstract:
            if field.__abstract__ and not abstract:
                abstract = True

            # change values in class data:
            if field.__static__:
                np_res_s[npk] = field
            else:
                np_res_i[npk] = field

        return np_res_s, np_res_i, abstract

    def __getattr_frombase(cls, name):
        """
        Internal helper function for getting an equivalent to super().name
        """
        cls_data = type.__getattribute__(cls, DATA)

        mro = list(cls_data.mro)
        # print(cls, mro)
        mro.pop(0)

        for entry in mro:
            try:
                return getattr(entry, name)
            except AttributeError:
                pass

        raise AttributeError(f"'{cls_data.name}' object's bases have no attribute '{name}'.")

    @classmethod
    def __scan_bases(mcs, mro, abstract):
        """
        Internal helper for scanning the bases of a type.
        """
        mro = list(mro)
        mro.pop(0)

        all_attrs = {}

        for entry in mro:
            all_attrs = mcs.__scan_type(entry, all_attrs)

        for ak, av in all_attrs.items():
            if av.__abstract__ and not abstract:
                return True
        return False

    @staticmethod
    def __scan_type(tp, attrdict):
        """
        Internal helper method for scanning a base of a type.
        """
        if isinstance(tp, MultiMeta):
            for fk, fv in tp.__data__.static_fields.items():
                if fk not in attrdict:
                    attrdict[fk] = fv
            return attrdict
        for ak, av in tp.__dict__.items():
            fv = _field.FieldWrapper(av)
            if ak not in attrdict:
                attrdict[ak] = fv
        return attrdict

    def __new__(mcs, *args, **kwargs):
        """
        Create a new multitools class.
        """
        # get common keyword argument + type check:
        abstract = kwargs.get('abstract', False)
        if not isinstance(abstract, bool):
            raise TypeError(f"'abstract': Expected type 'bool', got '{type(abstract).__name__}' instead.")

        match (len(args)):
            case 1:  # first overload is (MultiMeta, Optional[bool]) -> MultiMeta

                # type checking:
                source = args[0]
                if not isinstance(source, MultiMeta):
                    raise TypeError(f"'source': Expected type 'MultiMeta', got '{type(source).__name__}' instead.")

                # edit type:
                cls_data = type.__getattribute__(source, DATA)
                if cls_data.abstract != abstract:
                    cls_data.abstract = abstract
                type.__setattr__(source, DATA, cls_data)

                # return type:
                return source

            case 3:  # second overload is (str, Iterable[type], dict[str, Any], Optional[bool]) -> MultiMeta

                # get positional args + type check:
                name, bases, np = args
                if not isinstance(name, str):
                    raise TypeError(f"'name': Expected type 'str', got '{type(name).__name__}' instead.")
                if not _is_iter(bases):
                    raise TypeError(f"'bases': Expected type 'Iterable[type]', got '{type(bases).__name__}' instead.")
                if not isinstance(np, dict):
                    raise TypeError(f"'np': Expected type 'dict[str, Any]', got '{type(np).__name__}' instead.")
                for base in bases:
                    if not isinstance(base, type):
                        raise TypeError(f"'bases': Expected type 'Iterable[type]', got 'Iterable[{type(base).__name__}, ...]' instead.")
                bases = list(bases)
                bases.append(object)
                bases = tuple(bases)

                # get __doc__ and __fields__ + type check:
                doc = np['__doc__'] if '__doc__' in np else None
                field_defs = np['__fields__'] if '__fields__' in np else []
                if not isinstance(doc, (str, type(None))):
                    raise TypeError(f"'__doc__' must be str or None.")
                if not _is_iter(field_defs):
                    raise TypeError(f"'__fields__' must be an iterable of strings.")
                for field_name in field_defs:
                    if not isinstance(field_name, str):
                        raise TypeError(f"'__fields__' must be an iterable of strings.")
                    if field_name in DICT_VALID:
                        raise NameError(f"Illegal field name '{field_name}'.")

                # sort static and instance fields from np:
                static_fields, instance_fields, abstract = mcs.__sort_static_instance(np, field_defs, abstract=abstract)

                for base in bases:
                    if isinstance(base, MultiMeta):
                        print(type.__getattribute__(base, '__dict__'))
                        print(base.__data__.instance_fields)
                        # static_fields = {**static_fields, **base.__data__.static_fields}
                        instance_fields = {**instance_fields, **base.instance_fields}

                # create the new namespace:
                # noinspection PyTypeChecker
                new_np = {
                    DATA: _data.ClsData(name, abstract, field_defs, static_fields, instance_fields, bases, False, ()),
                    '__doc__': doc,
                }

                # if needed, propagate __classcell__ to the new class:
                if '__classcell__' in np:
                    new_np['__classcell__'] = np['__classcell__']

                # create new class:
                cls = type.__new__(mcs, name, bases, new_np)

                cls_mro = mcs.__get_mro(cls, bases)

                # update cls.__data__.abs_locked:
                cls_data = type.__getattribute__(cls, DATA)
                cls_data.abs_locked = mcs.__scan_bases(cls_mro, abstract)
                cls_data.mro = cls_mro
                type.__setattr__(cls, DATA, cls_data)

                # return class:
                return cls

            case _:  # wrong amount of args

                raise ValueError(f"'MultiMeta.__new__()' takes 1 or 3 positional arguments, but {len(args)} were given.")

    def __init__(cls, *args, **kwargs):
        """
        Initialize a new class.
        """
        if len(args) != 3:
            return  # cls.__init__() has already been called

        base_init = MultiMeta.__getattr_frombase(cls, '__init__')
        base_new = MultiMeta.__getattr_frombase(cls, '__new__')

        def _init(self, *a, **kw):
            if base_init is object.__init__:
                base_init(self)
            else:
                base_init(self, *a, **kw)

        # noinspection PyArgumentList
        def _new(c, *a, **kw):
            if base_new is object.__new__:
                return base_new(c)
            return base_new(c, *a, **kw)

        custom_init = cls.__data__.static_fields['__init__'].value if '__init__' in cls.__data__.static_fields else \
            _init
        custom_new = cls.__data__.static_fields['__new__'].value if '__new__' in cls.__data__.static_fields else \
            _new
        # print("creating", custom_init, custom_new)
        cls_data = type.__getattribute__(cls, DATA)

        def __init__(self, *initargs, **initkwargs):
            custom_init(self, *initargs, **initkwargs)

        def __new__(_cls, *newargs, **newkwargs):

            field_defs = _cls.__data__.field_defs
            self = custom_new(_cls, *newargs, **newkwargs)
            for field_name in field_defs:
                field = _cls.instance_attrs[field_name] if field_name in _cls.instance_attrs else _field.FieldWrapper(None)
                setattr(self, field_name, field.value)

            return self

        type.__init__(cls, *args, **kwargs)

        __init__.__qualname__ = f"{cls.__qualname__}.__init__"
        __new__.__qualname__ = f"{cls.__qualname__}.__new__"

        cls_data = type.__getattribute__(cls, DATA)
        # cls_data.static_fields['__init__'] = _field.FieldWrapper(__init__)
        # cls_data.static_fields['__new__'] = _field.FieldWrapper(__new__)
        type.__setattr__(cls, DATA, cls_data)

        # noinspection PyTypeChecker
        cls.__init__ = __init__
        cls.__new__ = __new__

    def __getattr__(cls, item):
        """
        Implement getattr(cls, name)
        """
        print("looking for", item)
        if item in DICT_VALID:
            # attribute can touch __dict__ so use builtin behaviour:
            return type.__getattribute__(cls, item)

        # get class data:
        cls_data = type.__getattribute__(cls, DATA)

        # attempt to find the attribute in cls:
        if item in cls_data.static_fields:
            res = cls_data.static_fields[item]
            if isinstance(res, _field.FieldWrapper):
                return res.value
            return res
        # upon failure, search in __mro__ entries for the attribute:
        mro = list(cls_data.mro)
        mro.pop(0)  # remove the class itself
        for entry in mro:
            try:
                return getattr(entry, item)
            except AttributeError:
                pass
        raise AttributeError(f"'{cls_data.name}' object has no attribute '{item}'.")

    def __setattr__(cls, key, value):
        """
        Implement self.key = value
        """
        if key in DICT_VALID:
            # attribute can touch __dict__:
            if isinstance(value, _field.FieldWrapper):
                value = value.value
            return type.__setattr__(cls, key, value)

        # get the class data:
        cls_data = type.__getattribute__(cls, DATA)

        # make a field with value if not already done:
        field = value if isinstance(value, _field.FieldWrapper) else _field.FieldWrapper(value)

        # here, a field defaults to a static one:
        if field.__static__ is None:
            field.__static__ = True

        # change value in class data:
        if field.__static__:
            cls_data.static_fields[key] = field
        else:
            cls_data.instance_fields[key] = field

        # update class data:
        type.__setattr__(cls, DATA, cls_data)

    def __call__(cls, *args, **kwargs):
        """
        Implement cls(*args, **kwargs)
        """
        if cls.__data__.abstract:
            raise TypeError(f"Cannot instantiate abstract class '{cls.__data__.name}'.")
        if cls.__data__.abs_locked:
            raise TypeError(f"Class '{cls.__data__.name}' missing overrides for one or more abstract fields.")

        new_method = getattr(cls, '__new__')
        init_method = getattr(cls, '__init__')
        print("running", new_method)
        self = new_method(cls, *args, **kwargs)
        print("running", init_method)
        init_method(self, *args, **kwargs)
        return self

    def __repr__(cls):
        """
        Implement repr(cls)
        """
        cls_data = type.__getattribute__(cls, DATA)
        return f"<multitools class '{cls_data.name}'>"

    __data__ = property(lambda cls: type.__getattribute__(cls, DATA))
    """Where everything about the class is stored."""
    instance_fields = property(lambda cls: cls.__data__.instance_fields)
    """Opens instance attributes to a read-only view from the outside."""



