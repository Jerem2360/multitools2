"""
Expected functionalities:

- @template([name=]<type>, [name=][<type>, <default>]) <class>
- @abstract  <class | method>
- <class>.dupe() -> class
- <class>.__template__ hook
-
"""
import sys
import types
import typing

from . import errors, runtime


_declaration_waiting_cache = {}


class _ArgWaitingDeclaration(type):
    def __new__(mcs, name, *args, **kwargs):
        cls = type.__new__(mcs, f"<template argument lock '{name}'>", (), {})
        return cls

    def __init__(cls, name, cb_args=()):
        cls._name = name
        cls._cb = lambda *args, **kwargs: None
        cls._cb_args = cb_args
        cls.value = None

    def cb(cls, cb):
        cls._cb = cb

    def assign(cls, tp):
        cls.value = tp
        cls._cb(cls.value, *cls._cb_args)


class _TemplateForwardReference:
    def __init__(self, name, globals_):
        self.name = name
        self._globals = globals_

    def __repr__(self):
        return f"<forward reference to type '{self.name}'>"

    def globals(self):
        return self._globals



class _WaitInfo:
    def __init__(self, owner, tvar_name, param_index, tparams, globals_):
        self._owner = owner
        self._owner_orig = owner.__origin__
        self._name = tvar_name
        self._pindex = param_index
        self._tparams = tparams
        self._t_globals = globals_

    def apply(self, type_obj):
        if self._name is not None:
            setattr(self._owner, self._name, type_obj)
        try:
            temp = list(self._owner.__targs__)
            temp[self._pindex] = type_obj
            self._owner.__targs__ = tuple(temp)
        except: pass

        new_tparams = []
        for tparam in self._tparams:
            if isinstance(tparam, _TemplateForwardReference):
                new_tparams.append(type_obj)
                continue
            new_tparams.append(tparam)

        self._owner.__origin__._typecache[self._owner.__targs__] = self._owner
        # print('o:', self._owner.__origin__._typecache)

        if tuple(self._tparams) in self._owner.__origin__._typecache:
            del self._owner.__origin__._typecache[tuple(self._tparams)]

    def globals(self):
        return self._t_globals


def abstract(op):
    """
    Decorated types and methods are made abstract.
    """
    if isinstance(op, type):
        if isinstance(op, (MultiMeta, TemplateType)) or issubclass(op, MultiMeta):
            op.__isabstract__ = True
    if isinstance(op, types.FunctionType):
        op.__isabstractmethod__ = True
    return op


class _Targ_t(type):
    def __new__(mcs, argno):
        return type.__new__(mcs, f"TArg[{argno}]", (), {})

    def __init__(cls, argno):
        cls._argno = argno


class TArg(type):
    """ """
    def __new__(mcs: 'TArg', *args, **kwargs):
        with errors.frame_mask:
            raise TypeError("Cannot instantiate a static type.")

    def __class_getitem__(mcs, item):
        return _Targ_t(item)

    def __getattr__(self, item):
        return type.__getattribute__(self, item)


def _tmp_signature(targs):
    res = '['
    for x in targs:
        if isinstance(x, _TemplateForwardReference):
            res += x.name
        elif isinstance(x, type):
            res += x.__name__
        else:
            res += repr(x)
        res += ', '
    res = res.removesuffix(', ')
    return res + ']'


def _update_name_in_module(op):
    runtime.scope_at(sys.modules[op.__module__])(op)



_T = typing.TypeVar("_T", covariant=True)


class MultiMeta(type):
    __isabstract__ = True
    _fwrd_refs_registry = {}

    def __new__(mcs, name, bases, np, **kwargs):
        from . import errors
        annot = np.get('__annotations__', {})

        if '__tvars__' not in np:
            tvars = {}
            # print(name, np)
            for k, v in annot.items():
                if isinstance(v, _Targ_t) and (k not in np):
                    tvars[v._argno] = k

            for v in tvars.values():
                del annot[v]
            np['__tvars__'] = tvars

        np['#kwargs'] = kwargs


        with errors.frame_mask:
            cls = type.__new__(mcs, name, bases, np, **kwargs)

        if name in mcs._fwrd_refs_registry:
            cls.register_forward_references(name)

        return cls

    def __init_subclass__(mcs, abstract=False, **kwargs):
        """
        Initialize a MultiMeta subtype (a metatype).
        'abstract' can be specified to make the metatype abstract.
        """
        mcs.__isabstract__ = abstract

    def __init__(cls, name, bases, np, **kwargs):
        type.__init__(cls, name, bases, np)
        if type(cls).__base__ is not type:
            if type(cls).__isabstract__:
                tmod = '' if type(cls).__module__ in ('builtins', '__main__') else type(cls).__module__ + '.'
                with errors.frame_mask:
                    raise TypeError(f"Cannot instantiate abstract type '{tmod}{type(cls).__qualname__}'.")

        if '__isabstract__' not in np:
            cls.__isabstract__ = False
            """Whether this type is abstract."""
        cls.__targs__: list | None = None

    def __call__(cls, *args, **kwargs):
        with errors.frame_mask:
            if cls.__isabstract__:
                tmod = '' if cls.__module__ in ('builtins', '__main__') else cls.__module__ + '.'
                raise TypeError(f"Cannot instantiate abstract type '{tmod}{cls.__qualname__}'.")

            if len(cls.__forward_refs__):
                raise TypeError(f"Cannot instantiate an incomplete type '{cls.__name__}': class '{cls.__forward_refs__[0]}' was never declared.")

            return type.__call__(cls, *args, **kwargs)

    def dup(cls: _T) -> _T:
        res = type(cls)(cls.__name__, cls.__bases__, dict(cls.__dict__), **getattr(cls, "#kwargs", {}))
        return res

    def register_forward_references(cls, name):
        i = -1
        for wi in MultiMeta._fwrd_refs_registry[name]:
            i += 1
            # print('g', wi.globals())
            # print('o', wi._owner_orig)
            if (wi._owner_orig.__name__ in wi.globals()) and (wi.globals()[wi._owner_orig.__name__] is wi._owner_orig):
                wi.apply(cls)
                MultiMeta._fwrd_refs_registry[name].pop(i)

    @property
    def __forward_refs__(cls):
        res = []
        if cls.__targs__ is None:
            return res
        for targ in cls.__targs__:
            if isinstance(targ, _TemplateForwardReference):
                res.append(targ.name)
        return res


class TemplateType(type):
    """
    Type for templates. Should not appear in places where normal types
    can appear.
    """
    def __new__(mcs, source, params, kwparams):
        cls = type.__new__(mcs, source.__name__, (), {'__module__': source.__module__})
        return cls

    def __init__(cls, source: type[_T], params, kwparams):
        cls.__source__ = source
        cls._typecache = {None: source}
        cls._frefs_typecache = {}
        cls.__argtypes__ = list([*params, *kwparams.values()])
        """cls.__name__ = cls.__source__.__name__ + '['
        cls.__qualname__ = cls.__source__.__qualname__ + '['
        for t in cls.__argtypes__:
            if isinstance(t, list) and len(t) == 2:
                t, d = t
            cls.__name__ += (t.__name__ + ', ')
            cls.__qualname__ += (t.__name__ + ', ')

        cls.__name__ = cls.__name__.removesuffix(', ') + ']'
        cls.__qualname__ = cls.__qualname__.removesuffix(', ') + ']'"""
        cls.__module__ = cls.__source__.__module__

        cls.__tnames__ = {}
        _annot = source.__annotations__
        i = -1
        for name, tp in _annot.items():
            i += 1
            if hasattr(source, name):
                continue
            if i >= len(cls.__argtypes__) or i < 0:
                continue
            d = None
            real_tp = cls.__argtypes__[i]
            if isinstance(real_tp, list) and len(real_tp) == 2:
                real_tp, d = real_tp
            if real_tp != tp:
                continue
            cls.__tnames__[name] = cls.__argtypes__[i]
            setattr(source, name, d)

    # passing template arguments as template[*args, *kwargs]
    def __getitem__(cls, item) -> type[_T]:

        if not isinstance(item, tuple):
            item = (item,)

        targs, has_fdecl = cls._make_targs(item, cls.__argtypes__, runtime.call_stack[1].f_globals)

        if has_fdecl:
            if tuple(targs) in cls._frefs_typecache:
                return cls._frefs_typecache[tuple(targs)]
        else:
            if tuple(targs) in cls._typecache:
                return cls._typecache[tuple(targs)]  # type: ignore

        res = cls.__source__.dup()
        res.__origin__ = cls
        res.__source__ = cls.__source__
        res.__name__ += _tmp_signature(targs)
        res.__qualname__ += _tmp_signature(targs)
        _update_name_in_module(res)

        for i in range(len(cls.__argtypes__)):

            targ, tparam = cls._get_tinfo(targs, i)
            if targ is NotImplemented:
                with errors.frame_mask:
                    raise TypeError(f"Missing required template argument n°{i+1}.")

            if not cls._parse_targ(targ, tparam):
                with errors.frame_mask:
                    raise TypeError(f"Template parameter {i+1} of type '{cls.__source__.__name__}': expected type {tparam}, got {type(targ)} instead.")

            tvar_name = cls._get_tvar_name(res, i)

            if tvar_name is not None:
                if isinstance(targ, _TemplateForwardReference):

                    wi = _WaitInfo(res, tvar_name, i, cls.__argtypes__, targ.globals())
                    if targ.name not in MultiMeta._fwrd_refs_registry:
                        MultiMeta._fwrd_refs_registry[targ.name] = []
                    MultiMeta._fwrd_refs_registry[targ.name].append(wi)

                setattr(res, tvar_name, targ)

        res.__targs__ = tuple(targs)

        return res

    # templates are not callable
    def __call__(cls, *args, **kwargs):
        with errors.frame_mask:
            raise TypeError("Templates cannot be instantiated.")

    def __repr__(cls):
        return f"<template '{cls.__qualname__}'>"

    # ref to source.__isabstract__
    @property
    def __isabstract__(cls):
        """
        Whether this type is abstract.
        """
        return cls.__source__.__isabstract__

    @__isabstract__.setter
    def __isabstract__(cls, value):
        # print("setting abstractness to", value)
        cls.__source__.__isabstract__ = value

    # ref to source.__targs__
    @property
    def __targs__(cls):
        return []  # this is always empty as templates themselves have no arguments

    def _get_tinfo(cls, targs, i):
        param_info = cls.__argtypes__[i]
        if not isinstance(param_info, list):
            param_info = [param_info]
        if len(param_info) == 2:
            tparam, tdefault = param_info
        else:
            tparam = param_info[0]
            tdefault = NotImplemented
        try:
            targ = targs[i]
        except IndexError:
            targ = tdefault
        return targ, tparam

    @staticmethod
    def _get_tvar_name(gi_result, i):
        result = None

        try:
            result = gi_result.__tvars__[i]
        except IndexError or KeyError:
            pass
        return result

    @staticmethod
    def _parse_targ(targ, tparam):
        if isinstance(targ, tparam):
            return True
        if issubclass(tparam, type) and isinstance(targ, _TemplateForwardReference):
            return True
        return False

    @classmethod
    def _make_targs(mcs, targs, tparams, glob):
        res = []

        has_fdecl = False
        i = -1
        for targ in targs:
            i += 1
            if isinstance(targ, str) and issubclass(tparams[i], type):
                if targ in glob and isinstance(glob[targ], type):
                    res.append(glob[targ])
                    continue
                has_fdecl |= True
                tfd = _TemplateForwardReference(targ, glob)
                res.append(tfd)
                continue
            res.append(targ)

        return res, has_fdecl


def template(*params, **kwparams):
    """
    Make a type a template type.
    Template types cannot be used as normal types:
    They require passing template arguments in order to
    act as normal types.

    e.g: template() is meaningless, as opposed to template[*args, ...]()


    usage:

    @template(name=type, name1=type1, name2=type2, ...)
    class C: ...


    @template(type, type1, type2)
    class C: ...
    """
    return lambda op: TemplateType(op, params, kwparams)

