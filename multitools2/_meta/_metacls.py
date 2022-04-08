# imports:
import sys
from dataclasses import dataclass

from ._const import *
from ._locals import *


class MultiMeta(MultiType):
    def __new__(mcs, *args, **kwargs):

        # keyword argument 'decorations', always available:
        decorations = kwargs.get('decorations', [])

        # type checking:
        if not isinstance(decorations, list):
            raise TypeError(TYPE_ERROR_STR.format('decorations', 'list[str]', type(decorations).__name__))
        for decoration in decorations:
            if not isinstance(decoration, str):
                raise TypeError(
                    TYPE_ERROR_STR.format('decorations', 'list[str]', f"list[{type(decoration).__name__}, ...]"))

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
                    mt_init = np[INIT] if is_function(np[INIT]) else None
                    del np[INIT]

                mt_new = None
                if NEW in np:
                    mt_new = np[NEW] if is_function(np[NEW]) else None
                    del np[NEW]

                mt_getattribute = None
                if GETATTRIBUTE in np:
                    mt_getattribute = np[GETATTRIBUTE] if is_function(np[GETATTRIBUTE]) else None
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
                for an, av in np.items():
                    field = assure_field(av)

                    # if field is a function, defaults to instance, otherwise defaults to static:
                    if is_function(av):
                        if has_dec(field, DEC_STATIC) and an not in mt_field_defs:
                            mt_static[an] = field
                            continue
                        mt_instance[an] = field
                        if has_dec(field, DEC_CALLBACK):
                            mt_static[an] = field
                        continue

                    if (an in mt_field_defs) and (not has_dec(field, DEC_STATIC)):
                        mt_instance[an] = field
                        continue
                    mt_static[an] = field

                # build class data
                mt_data = Data(
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
                    MRO: tuple(mt_mro),
                    NAME: name,
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
            print(c, newargs, newkwargs)
            if d_new is not None:
                self = d_new(c, *newargs, **newkwargs)
            else:
                base_new = super(c).__new__
                try:
                    self = base_new(c, *newargs, **newkwargs)
                except TypeError:
                    self = base_new(c)
            for fk, fv in mt_data.instance.items():
                self.__setattr__(fk, fv.value(self, c))
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

            return value.value(self, cls) if isinstance(value, Field) else value

        # update __qualname__ depending on the class:
        __init__.__qualname__ = f"{mt_data.name}.{INIT}"
        __new__.__qualname__ = f"{mt_data.name}.{NEW}"
        __getattribute__.__qualname__ = f"{mt_data.name}.{GETATTRIBUTE}"

        # update __init__, __new__ and __getattribute__ in the class __dict__:
        type.__setattr__(cls, INIT, __init__)
        type.__setattr__(cls, NEW, __new__)
        type.__setattr__(cls, GETATTRIBUTE, __getattribute__)

        # add __init__, __new__ and __getattribute__ to the static fields:
        mt_data.static[INIT] = Field(__init__)
        mt_data.static[NEW] = Field(__new__)
        mt_data.static[GETATTRIBUTE] = Field(__getattribute__)

        type.__setattr__(cls, SEC_DATA, mt_data)

    def __getattr__(cls, item):
        # fetch class data:
        mt_data = type.__getattribute__(cls, SEC_DATA)

        # look for item in mt_data.static:
        if item in mt_data.static:
            res = mt_data.static[item].value(None, cls) if isinstance(mt_data.static[item], Field) else mt_data.static[item]
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
        field = assure_field(value)

        # if field is abstract, make the entire class abstract:
        if has_dec(field, DEC_ABSTRACT):
            mt_data.flags |= FLAG_ABSTRACT

        # if field is a callback field, update __dict__, static and instance:
        if has_dec(field, DEC_CALLBACK):
            mt_data.static[key] = field
            mt_data.instance[value] = field
            type.__setattr__(key, field.value(None, cls))

        else:
            # update static or instance depending on the property of field:
            if has_dec(field, DEC_STATIC):
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
            if isinstance(entry, MultiMeta):
                base_data = type.__getattribute__(entry, SEC_DATA)
                for sk, sv in base_data.static.items():
                    if has_dec(sv, DEC_ABSTRACT) and (sk not in mt_data.static):
                        raise TypeError(ABS_OVERRIDE_ERROR_STR.format(mt_data.name, sk))
                for ik, iv in base_data.instance.items():
                    if has_dec(iv, DEC_ABSTRACT) and (ik not in mt_data.instance):
                        raise TypeError(ABS_OVERRIDE_ERROR_STR.format(mt_data.name, ik))
            else:
                for k, v in entry.__dict__.items():
                    if has_dec(v, DEC_ABSTRACT) and (k not in mt_data.instance) and (k not in mt_data.static):
                        raise TypeError(ABS_OVERRIDE_ERROR_STR.format(mt_data.name, k))

        # call cls.__new__()
        try:
            self = cls.__new__(cls, *args, **kwargs)
        except Exception as e:
            raise type(e)(*e.args)

        # update self.__dict__ with instance attributes:
        for fk, fv in mt_data.instance.items():
            setattr(self, fk, fv.value(self, cls))

        # call self.__init__()
        try:
            self.__init__(self, *args, **kwargs)
        except Exception as e:
            raise type(e)(*e.args)

        return self

    __data__ = property(lambda cls: type.__getattribute__(cls, SEC_DATA))

