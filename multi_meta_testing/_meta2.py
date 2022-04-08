# imports:
import sys
from dataclasses import dataclass


class MultiType(type):
    def __repr__(cls):
        return f"<multitools class '{cls.__name__}'>"


# attribute decorations names:
DEC_ABSTRACT = '__abstract__'
DEC_STATIC = '__static__'
DEC_CALLBACK = '__callback__'

# secret names:
SEC_DATA = '#00'
SEC_TEMP_INIT = '#01'
SEC_TEMP_NEW = '#02'
SEC_TEMP_GETATTRIBUTE = '#03'
SEC_VALUE = '#04'

# error format strings:
TYPE_ERROR_STR = "'{0}': Expected type '{1}', got '{2}' instead."
ATTR_ERROR_STR = "'{0}' has no attribute '{1}'."
POS_ARG_ERROR_STR = "'{0}' takes {1} positional arguments, but {2} were given."

# multimeta flags:
FLAG_ABSTRACT = 1
FLAG_STATIC = 10

# other:
ITER = '__iter__'
FIELDS = '__fields__'
CLASSCELL = '__classcell__'
INIT = '__init__'
NEW = '__new__'
GETATTRIBUTE = '__getattribute__'


def _has_dec(value, dec):
    """
    Return whether the provided field has been decorated in the specified way.
    """
    try:
        return getattr(value, dec)
    except AttributeError:
        return False


def _give_dec(value, dec):
    """
    Decorate the provided field in the provided way and return it.
    """
    setattr(value, dec, True)
    return value


def _is_function(obj):
    """
    Return whether and object is a function / method or not.
    """
    func_t = type(lambda: None)
    builtin_func_t = type(print)
    return isinstance(obj, (func_t, builtin_func_t, staticmethod, classmethod))


class _Field(metaclass=MultiType):

    def __init__(self, value):
        super().__setattr__(SEC_VALUE, value)

    value = property(lambda self: super().__getattribute__(SEC_VALUE))
    is_function = property(lambda self: _is_function(self.value))


@dataclass
class _Data(metaclass=MultiType):
    name: str
    bases: tuple[type]
    static: dict[str, _Field]
    instance: dict[str, _Field]
    mro: list[type]
    flags: int


def _assure_field(value):
    """
    Convert value to a field if necessary. The result is guaranteed to be a
    field object.
    """
    return value if isinstance(value, _Field) else _Field(value)


class MultiMeta(MultiType):
    def __new__(mcs, *args, **kwargs):

        # keyword argument 'decorations', always available:
        decorations = kwargs.get('decorations', [])

        # type checking:
        if not isinstance(decorations, list):
            raise TypeError(TYPE_ERROR_STR.format('decorations', 'list[str]', type(decorations).__name__))
        for decoration in decorations:
            if not isinstance(decoration, str):
                raise TypeError(TYPE_ERROR_STR.format('decorations', 'list[str]', f"list[{type(decoration).__name__}, ...]"))

        match len(args):
            # first overload (name: str, bases: tuple, np: dict, decorations=[]) -> MultiMeta:
            case 3:
                name, bases, np = args

                # type checking:
                if not isinstance(name, str):
                    raise TypeError(TYPE_ERROR_STR.format('name', 'str', type(name).__name__))

                if not hasattr(bases, ITER):
                    raise TypeError("'bases' must be an iterable such as a list or a tuple.")

                if not isinstance(np, dict):
                    raise TypeError(TYPE_ERROR_STR.format('np', 'dict[str, Any]', type(name).__name__))

                mt_flags = 0
                # flag management:
                if DEC_STATIC in decorations:
                    mt_flags |= FLAG_STATIC
                if DEC_ABSTRACT in decorations:
                    mt_flags |= FLAG_ABSTRACT

                # propagate __classcell__:
                mt_classcell = None
                if CLASSCELL in np:
                    mt_classcell = np[CLASSCELL]
                    del np[CLASSCELL]

                # save __init__, __new__ and __getattribute__ for MultiMeta.__init__():
                mt_init = None
                if INIT in np:
                    mt_init = np[INIT] if _is_function(np[INIT]) else None
                    del np[INIT]

                mt_new = None
                if NEW in np:
                    mt_new = np[NEW] if _is_function(np[NEW]) else None
                    del np[NEW]

                mt_getattribute = None
                if GETATTRIBUTE in np:
                    mt_getattribute = np[GETATTRIBUTE] if _is_function(np[GETATTRIBUTE]) else None
                    del np[GETATTRIBUTE]

                # fetch eventual field defs:
                mt_field_defs = []
                if FIELDS in np:
                    mt_field_defs = np[FIELDS]
                    del np[FIELDS]

                # build mro:
                mt_mro = [*bases]
                if type not in bases:
                    mt_mro.append(object)

                # sort fields:
                mt_static = {}
                mt_instance = {}
                for an, av in np:
                    field = _assure_field(av)

                    # if field is a function, defaults to instance, otherwise defaults to static:
                    if _is_function(av):
                        if _has_dec(field, DEC_STATIC):
                            mt_static[an] = field
                            continue
                        mt_instance[an] = field
                        if _has_dec(field, DEC_CALLBACK):
                            mt_static[an] = field
                        continue

                    if (an in mt_field_defs) and (not _has_dec(field, DEC_STATIC)):
                        mt_instance[an] = field
                        continue
                    mt_static[an] = field

                # build class data
                mt_data = _Data(
                    name,
                    tuple(bases),
                    mt_static,
                    mt_instance,
                    mt_mro,
                    mt_flags,
                )

                # build new namespace for future class:
                new_np = {
                    SEC_DATA: mt_data,
                    SEC_TEMP_INIT: mt_init,
                    SEC_TEMP_NEW: mt_new,
                    SEC_TEMP_GETATTRIBUTE: mt_getattribute,
                }
                # propagate __classcell__:
                if mt_classcell is not None:
                    new_np[CLASSCELL] = mt_classcell

                mt = type.__new__(mcs, name, bases, new_np)
                return mt

            # second overload (source: MultiMeta, decorations: list) -> MultiMeta
            case 1:
                source = args[0]
                if not isinstance(source, MultiMeta):
                    raise TypeError(TYPE_ERROR_STR.format('source', 'MultiMeta', type(source).__name__))

                mt_data = type.__getattribute__(source, SEC_DATA)

                mt_flags = 0
                # flag management:
                if DEC_STATIC in decorations:
                    mt_flags |= FLAG_STATIC
                if DEC_ABSTRACT in decorations:
                    mt_flags |= FLAG_ABSTRACT

                mt_data.flags = mt_flags
                type.__setattr__(source, SEC_DATA, mt_data)
                return source

            case _:
                raise ValueError(POS_ARG_ERROR_STR.format('MultiMeta.__new__', '1 or 3', len(args)))

    def __init__(cls, *args, **kwargs):
        # do something for first overload only:
        if len(args) != 3:
            return

        type.__init__(cls, *args)

        # get __init__, __new__ and __getattribute__ that were defined in the original namespace:
        d_init = type.__getattribute__(cls, SEC_TEMP_INIT)
        d_new = type.__getattribute__(cls, SEC_TEMP_NEW)
        d_getattribute = type.__getattribute__(cls, SEC_TEMP_GETATTRIBUTE)

        # del their temporary storage variables:
        type.__delattr__(cls, SEC_TEMP_INIT)
        type.__delattr__(cls, SEC_TEMP_NEW)
        type.__delattr__(cls, SEC_TEMP_GETATTRIBUTE)

        mt_data = type.__getattribute__(cls, SEC_DATA)

        # define real __init__, __new__ and __getattribute__:
        def __init__(self, *initargs, **initkwargs):
            if d_init is not None:
                return d_init(self, *initargs, **initkwargs)
            base_init = super(type(self), self).__init__
            try:
                base_init(self, *initargs, **initkwargs)
            except TypeError:
                base_init(self)

        def __new__(c, *newargs, **newkwargs):
            if d_new is not None:
                self = d_new(c, *newargs, **newkwargs)
            else:
                base_new = super(c).__new__
                try:
                    self = base_new(c, *newargs, **newkwargs)
                except TypeError:
                    self = base_new(c)
            for fk, fv in mt_data.instance.items():
                self.__setattr__(fk, fv.value)
            return self

        def __getattribute__(self, name):
            if d_getattribute is not None:
                return d_getattribute(self, name)

            try:
                value = object.__getattribute__(self, '__getattr__')(name)
            except AttributeError:
                value = object.__getattribute__(self, name)

            if hasattr(value, '__get__'):
                value = value.__get__(self, type(self))

            return value.value if isinstance(value, _Field) else value

        # update __qualname__ depending on the class:
        __init__.__qualname__ = f"{mt_data.name}.{INIT}"
        __new__.__qualname__ = f"{mt_data.name}.{NEW}"
        __getattribute__.__qualname__ = f"{mt_data.name}.{GETATTRIBUTE}"

        # update __init__, __new__ and __getattribute__ in the class __dict__:
        type.__setattr__(cls, INIT, __init__)
        type.__setattr__(cls, NEW, __new__)
        type.__setattr__(cls, GETATTRIBUTE, __getattribute__)

        # add __init__, __new__ and __getattribute__ to the static fields:
        mt_data.static[INIT] = _Field(__init__)
        mt_data.static[NEW] = _Field(__new__)
        mt_data.static[GETATTRIBUTE] = _Field(__getattribute__)

        type.__setattr__(cls, SEC_DATA, mt_data)

    def __getattr__(cls, item):
        # fetch class data:
        mt_data = type.__getattribute__(cls, item)

        # look for item in mt_data.static:
        if item in mt_data.static:
            res = mt_data.static[item].value if isinstance(mt_data.static[item], _Field) else mt_data.static[item]
            if hasattr(res, '__get__'):
                return res.__get__(None, cls)
            return res

        # if not found, search in __mro__:
        for entry in mt_data.mro:
            try:
                res = getattr(entry, item)
                if hasattr(res, '__get__'):
                    return res.__get__(None, cls)
                return res
            except AttributeError | ValueError:
                pass

        # re-raise the last error:
        err = sys.exc_info()[0](*sys.exc_info()[1].args)
        if isinstance(err, (ValueError, AttributeError)):
            raise err
        raise AttributeError(ATTR_ERROR_STR.format(mt_data.name, item))

    def __setattr__(cls, key, value):
        # fetch class data:
        mt_data = type.__getattribute__(cls, SEC_DATA)

        # make sure value is a field:
        field = _assure_field(value)

        # if field is abstract, make the entire class abstract:
        if _has_dec(field, DEC_ABSTRACT):
            mt_data.flags |= FLAG_ABSTRACT

        # if field is a callback field, update __dict__, static and instance:
        if _has_dec(field, DEC_CALLBACK):
            mt_data.static[key] = field
            mt_data.instance[value] = field
            type.__setattr__(key, field.value)

        else:
            # update static or instance depending on the property of field:
            if _has_dec(field, DEC_STATIC):
                mt_data.static[key] = field
            else:
                mt_data.instance[key] = field

        # update class data:
        type.__setattr__(cls, SEC_DATA, mt_data)

    def __call__(cls, *args, **kwargs):
        # fetch class data:
        mt_data = type.__getattribute__(cls, SEC_DATA)

        # make sure class is not abstract:
        flag_digits = [*str(mt_data.flags)]
        flag_abstract = int(flag_digits[0])
        if flag_abstract > 0:
            raise TypeError(f"Can't instantiate an abstract class.")

        # make sure all abstract fields of parent classes are overridden:
        for entry in mt_data.mro:
            base_attrs = entry.__dict__
            if isinstance(entry, MultiMeta):
                base_data = type.__getattribute__(entry, SEC_DATA)
                for sk, sv in base_data.static.items():
                    if sv.abstract and sk not in mt_data.static:
                        pass

        # call cls.__new__()
        try:
            self = cls.__new__(*args, **kwargs)
        except Exception as e:
            raise type(e)(*e.args)

        # update self.__dict__ with instance attributes:
        for fk, fv in mt_data.instance.items():
            setattr(self, fk, fv.value)

        # call self.__init__()
        try:
            self.__init__(self, *args, **kwargs)
        except Exception as e:
            raise type(e)(*e.args)

        return self

    __data__ = property(lambda cls: type.__getattribute__(cls, SEC_DATA))

