import dataclasses
import types

from ._tp_check import *

from dataclasses import dataclass
from typing import Iterable
import sys


# attributes created by decorators:
DEC_CALLBACK = '__calllback__'
DEC_ABSTRACT = '__abstract__'
DEC_STATIC = '__static__'

DATA = '#00'  # hexadecimal attribute id
CLASSCELL = '__classcell__'
INIT = '__init__'
NEW = '__new__'
GETATTR = '__getattribute__'
MRO = '__mro__'
# temporary storage places for __init__, __new__ and __getattribute__:
INIT_TEMP = '#02'  # hex
NEW_TEMP = '#01'  # hex
GETATTR_TEMP = '#03'  # hex


def _has_dec(obj, dec):
    return hasattr(obj, dec) and getattr(obj, dec)


def _propagate_name(np_source, np_dest, name):
    if name in np_source:
        np_dest[name] = np_source[name]
    return np_dest


def is_static(item, default=False):
    if hasattr(item, '__static__') and isinstance(item.__static__, bool):
        return item.__static__
    return default


def is_abs(item, default=False):
    if hasattr(item, '__abstract__') and isinstance(item.__abstract__, bool):
        return item.__abstract__
    return default


def is_opt_func(item):
    return callable(item) or (item is None)

def _inst_hasattr(instance, name):
    try:
        object.__getattribute__(instance, name)
    except:
        return False
    return True

def _find_in_tp(tp, name):
    if DATA in type.__getattribute__(tp, '__dict__'):  # isinstance(tp, MultiMeta)
        mt_data = type.__getattribute__(tp, DATA)
        if name in mt_data.static:
            return mt_data.static[name]
        return
    return type.__getattribute__(tp, name)


def _find_in_mro(mt, name, **kwargs):
    """
    res = _find_in_tp(mt, name)
    if res is not None:
        return res.value if isinstance(res, Field) else res

    try:
        _mro = kwargs.get('mro', mt.__mro__)
    except AttributeError:
        return

    for entry in _mro:
        res = _find_in_tp(entry, name)
        if res is None:
            continue
        return res.value if isinstance(res, Field) else res
    return
    """
    pass


class Field:
    def __init__(self, value):
        if isinstance(value, Field):
            raise TypeError("Can't store fields inside fields.")
        self._v = value

    value = property(lambda self: self._v)


@dataclasses.dataclass
class Data:
    static: dict[str, Field]
    instance: dict[str, Field]
    bases: tuple[type]
    name: str
    mro: Iterable[type]
    abstract: bool


class MultiMeta(type):
    @staticmethod
    def instance_getattr(self, name, base_ga=object.__getattribute__):
        try:
            value = base_ga(self, name)
        except AttributeError:
            if hasattr(self, '__getattr__'):
                value = self.__getattr__(name)
            else:
                raise

        if isinstance(value, Field):
            value = value.value

        res = value.__get__(self, type(self)) if hasattr(value, '__get__') else value
        return res

    def __set_static(cls, name, value):
        mt_data = type.__getattribute__(cls, DATA)
        field = value if isinstance(value, Field) else Field(value)

        mt_data.static[name] = field

        type.__setattr__(cls, DATA, mt_data)

    def __set_instance(cls, name, value):
        mt_data = type.__getattribute__(cls, DATA)
        field = value if isinstance(value, Field) else Field(value)

        mt_data.instance[name] = field

        type.__setattr__(cls, DATA, mt_data)

    def __get_static(cls, name):
        mt_data = type.__getattribute__(cls, DATA)
        try:
            if is_abs(mt_data.static[name]):
                raise ValueError(f"'{name}' field is abstract.")
            return mt_data.static[name].value
        except KeyError or AttributeError:
            raise AttributeError(ATTR_ERROR_STR.format(type(cls), name))
        except:
            pass
        raise sys.exc_info()[0](*sys.exc_info()[1].args)

    def __get_instance(cls, name):
        mt_data = type.__getattribute__(cls, DATA)
        try:
            if is_abs(mt_data.static[name]):
                raise ValueError(f"'{name}' field is abstract.")
            return mt_data.static[name].value
        except KeyError or AttributeError:
            raise AttributeError(ATTR_ERROR_STR.format(type(cls), name))
        except:
            pass
        raise sys.exc_info()[0](*sys.exc_info()[1].args)

    def __new__(mcs, *args, **kwargs):

        abstract = kwargs.get('abstract', False)
        if not isinstance(abstract, bool):
            raise TypeError(TYPE_ERROR_STR.format('abstract', 'bool', type(abstract).__name__))

        match len(args):
            case 3:  # first overload:
                name, bases, np = args  # fetch params

                # type checking:
                if not isinstance(name, str):
                    raise TypeError(TYPE_ERROR_STR.format('name', 'str', type(name).__name__))
                if not isinstance(bases, (tuple, list)):
                    raise TypeError(TYPE_ERROR_STR.format('bases', 'tuple[type]', type(bases).__name__))
                if not isinstance(np, dict):
                    raise TypeError(TYPE_ERROR_STR.format('np', 'dict[str, Any]', type(np).__name__))

                ifield_defs = [] if '__fields__' not in np else list(np['__fields__'])
                if '__fields__' in np:
                    del np['__fields__']

                # build mro:
                mt_mro = [*bases]
                if type not in bases:
                    mt_mro.append(object)

                # separate static and instance fields:
                static_fields = {}
                instance_fields = {}

                for npk, npv in np.items():
                    field = npv if isinstance(npv, Field) else Field(value)

                    # if callable, the field defaults to instance, otherwise static:
                    default_s = True
                    if callable(field.value):
                        default_s = False

                    # put the field in the right dict:
                    if (not is_static(field, default=default_s)) or (npk in ifield_defs):
                        instance_fields[npk] = field
                        continue
                    static_fields[npk] = field

                # assemble class data:
                mt_data = Data(
                    static_fields,    # static
                    instance_fields,  # instance
                    tuple(bases),     # bases
                    name,             # name
                    tuple(mt_mro),    # mro
                    abstract,         # abstract
                )

                # namespace of the multitools type:
                mt_np = {
                    DATA: mt_data,
                    INIT_TEMP: None,
                    NEW_TEMP: None,
                    GETATTR_TEMP: None,
                    MRO: mt_mro,
                }

                # propagate names:
                mt_np = _propagate_name(np, mt_np, CLASSCELL)
                for ak, av in static_fields.items():
                    if _has_dec(av, DEC_CALLBACK):
                        instance_fields[ak] = av

                if INIT in np:
                    mt_np[INIT_TEMP] = np[INIT]
                if NEW in np:
                    mt_np[NEW_TEMP] = np[NEW]
                if GETATTR in np:
                    mt_np[GETATTR_TEMP] = np[GETATTR]

                # initialize multitools type:
                mt = type.__new__(mcs, name, bases, mt_np)
                return mt

            case 1:
                source = args[0]
                if not isinstance(source, MultiMeta):
                    raise TypeError(TYPE_ERROR_STR.format('source', 'MultiMeta', type(source).__name__))

                mt_data = type.__getattribute__(source, DATA)
                if mt_data.abstract != abstract:
                    mt_data.abstract = abstract
                type.__setattr__(source, DATA, mt_data)
                return source

            case _:
                raise ValueError(ARG_ERROR_STR.format('MultiMeta.__new__()', '1 or 3', len(args)))

    def __init__(cls, *args, **kwargs):
        if len(args) != 3:
            return

        super().__init__(*args, **kwargs)

        mt_data = type.__getattribute__(cls, DATA)
        ifields = mt_data.instance

        # get temporary stored methods:
        original_getattr = type.__getattribute__(cls, GETATTR_TEMP)
        original_new = type.__getattribute__(cls, NEW_TEMP)
        original_init = type.__getattribute__(cls, INIT_TEMP)

        # remove them from cls.__dict__:
        type.__delattr__(cls, GETATTR_TEMP)
        type.__delattr__(cls, NEW_TEMP)
        type.__delattr__(cls, INIT_TEMP)

        # type check them:
        if not is_opt_func(original_getattr):
            raise TypeError("__getattribute__ must be callable.")
        if not is_opt_func(original_new):
            raise TypeError("__new__ must be callable.")
        if not is_opt_func(original_init):
            raise TypeError("__init__ must be callable.")

        ##------  Instance Methods ------##

        # define __getattribute__, __init__ and __new__:
        def __getattribute__(self, name):
            # case where the current class has __getattribute__:
            if original_getattr is not None:
                return original_getattr(self, name)
            # case where super(type(self)) has __getattribute__:
            return MultiMeta.instance_getattr(self, name, base_ga=super(cls, self).__getattribute__)

        def __init__(self, *initargs, **initkwargs):
            # case where the current class has __init__:
            if original_init is not None:
                original_init(self, *initargs, **initkwargs)
            # case where super(type(self)) has __init__:
            base_init = super(cls, self).__init__
            if base_init is object.__init__:
                return base_init(self)
            return base_init(self, *initargs, **initkwargs)

        def __new__(c, *newargs, **newkwargs):
            # case where the current class has __new__:
            if original_new is not None:
                return original_new(c, *newargs, **newkwargs)
            # case where super(type(self)) has __new__:
            base_new = super(cls).__new__
            if base_new is object.__new__:
                self = base_new(c)
            else:
                self = base_new(c, *newargs, **newkwargs)
            for fk, fv in ifields.items():
                val = fv.value if isinstance(fv, Field) else fv
                setattr(self, fk, val)
            return self

        # update qualnames:
        __getattribute__.__qualname__ = f"{cls.__qualname__}.{GETATTR}"
        __init__.__qualname__ = f"{cls.__qualname__}.{INIT}"
        __new__.__qualname__ = f"{cls.__qualname__}.{NEW}"

        # store __getattribute__, __init__ and __new__ into cls.__dict__:
        type.__setattr__(cls, GETATTR, __getattribute__)
        type.__setattr__(cls, INIT, __init__)
        type.__setattr__(cls, NEW, __new__)

        # store __getattribute__, __init__ and __new__ into static fields:
        mt_data.static[GETATTR] = __getattribute__
        mt_data.static[INIT] = __init__
        mt_data.static[NEW] = __new__

        # update class data:
        type.__setattr__(cls, DATA, mt_data)



