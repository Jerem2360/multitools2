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

import _ctypes

from . import errors, runtime, type_check
from .._internal._typeshed import *


_T = typing.TypeVar('_T')


_declaration_waiting_cache = {}

_dir_singleton = ['__bool__', '__class__', '__delattr__', '__dir__', '__doc__', '__eq__', '__format__', '__getattribute__', '__repr__']

def _ensure_no_arguments(func):
    if hasattr(func, '__code__'):
        if func.__code__.co_argcount != 1:
            raise TypeError(f"Singleton constructors must accept no argument but 'self' or 'cls'.") from errors.configure(depth=1)
    if hasattr(func, '__text_signature__'):
        if func.__text_signature__ is None:
            return
        arglist_raw = func.__text_signature__.split(', ')

        arglist = []
        for a in arglist_raw:
            a = a.removeprefix('(').removesuffix(')')
            if a not in ('/', '*'):
                arglist.append(a)

        if len(arglist) != 1:
            raise TypeError(f"Singleton constructors must accept no argument but 'self' or 'cls'.") from errors.configure(depth=1)


class Singleton:
    """
    Featureless unique values.
    Instantiating their types returns themselves.
    Analog to None, NotImplemented, and such.

    usage:

    example = Singleton(name="example")

    @Singleton
    class example:
        ...


    Note:
    If the singleton defines constructors, they must accept no argument.
    """

    def __new__(cls, body: type = None, /, *, name: str = None) -> object:

        decl_new = object.__new__ if body is None else getattr(body, '__new__', object.__new__)

        with errors.frame_mask:
            _ensure_no_arguments(decl_new)

        # the singleton's methods:
        def _repr(self):
            return type(self).__name__.removesuffix('_t')

        _repr.__name__ = '__repr__'

        def _new(cls):
            if cls._cache is None:
                cls._cache = decl_new(cls)  # type: ignore
            return cls._cache

        _new.__name__ = '__new__'

        def _call(self):
            with errors.frame_mask:
                raise TypeError(f"Singleton '{repr(self)}' is not callable")

        _call.__name__ = '__call__'

        def _dir(self):
            return _dir_singleton

        _dir.__name__ = '__dir__'

        def _bool(self):
            return True

        _bool.__name__ = '__bool__'

        def _format(self):
            return repr(self)

        _format.__name__ = '__format__'

        # creating the singleton:
        if body is None:
            if name is None:
                raise TypeError("Singletons must specify a name.") from errors.configure(depth=1)

            _repr.__qualname__ = name + '_t.__repr__'
            _new.__qualname__ = name + '_t.__new__'
            _call.__qualname__ = name + '_t.__call__'
            _dir.__qualname__ = name + '_t.__dir__'
            _bool.__qualname__ = name + '_t.__bool__'
            _format.__qualname__ = name + '_t.__format__'

            typeobj = type(name + '_t', (), {'__slots__': (), '__new__': _new, '__call__': _call, '__dir__': _dir, '__bool__': _bool, '__format__': _format})
        else:
            _repr.__qualname__ = body.__name__ + '_t.__repr__'
            _new.__qualname__ = body.__name__ + '_t.__new__'
            _call.__qualname__ = body.__name__ + '_t.__call__'
            _dir.__qualname__ = body.__name__ + '_t.__dir__'
            _bool.__qualname__ = body.__name__ + '_t.__bool__'
            _format.__qualname__ = body.__name__ + '_t.__format__'

            np = dict(body.__dict__)

            if '__init__' in np:
                with errors.frame_mask:
                    _ensure_no_arguments(np['__init__'])

            if '__repr__' not in np:
                np['__repr__'] = _repr
            if '__bool__' not in np:
                np['__bool__'] = _bool
            if '__format__' not in np:
                np['__format__'] = _format

            slots = np.get('__slots__', ())

            for n in slots:
                if (n in np) and isinstance(np[n], MemberDescriptor):
                    del np[n]

            if is_abstract(body):
                raise TypeError("Singletons cannot be abstract.") from errors.configure(depth=1)

            kwargs = {} if not isinstance(body, MultiMeta) else getattr(body, '#kwargs', {})

            typeobj = type.__new__(type, body.__name__ + '_t', body.__bases__, {**np, '__module__': body.__module__, '__slots__': slots, '__new__': _new, '__call__': _call, '__dir__': _dir, '__doc__': body.__doc__}, **kwargs)
            if is_final(body):
                typeobj = final(typeobj)

        typeobj._cache = None

        try:
            return typeobj()
        except:
            raise TypeError("Singleton constructors must accept no argument but 'self' or 'cls'.") from errors.configure(depth=1)


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


def abstract(op: _T) -> _T:
    """
    Decorated types and methods are made abstract.
    """
    if isinstance(op, type):
        if isinstance(op, (MultiMeta, TemplateType)) or issubclass(op, MultiMeta):
            op.__isabstract__ = True
    if isinstance(op, types.FunctionType):
        op.__isabstractmethod__ = True
    return op


def final(op: _T) -> _T:
    """
    Decorated types can no longer be subclassed.
    This is checked at runtime.
    """
    op.__isfinal__ = True
    return op


def is_abstract(tp: type):
    """
    Return whether a given type is abstract or not.
    Supports custom MultiMeta types as well as builtin and extension
    abstract types.
    """
    if hasattr(tp, '__isabstract__'):
        return tp.__isabstract__
    return bool(tp.__flags__ & (1 << 20)) or '__new__' not in tp.__dict__


def is_final(tp: type):
    """
    Return whether a given type is final or not.
    Supports custom MultiMeta types as well as builtin and
    extension final types.
    """
    return getattr(tp, '__isfinal__', False) or not (tp.__flags__ & (1 << 10))


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


class MultiMeta(type):
    __isabstract__ = True
    _fwrd_refs_registry = {}

    def __new__(mcs, name, bases, np, **kwargs):
        from . import errors
        annot = np.get('__annotations__', {})

        _inherit_templates = []
        _fixed_bases = []

        for b in bases:
            # support for final types, as well as builtin and extension final types:
            _final = getattr(b, '__isfinal__', False) or not (b.__flags__ & (1 << 10))
            if _final:
                raise TypeError(f"Cannot inherit from final class '{b.__name__}'.") from errors.configure(depth=1)

            if isinstance(b, TemplateType):
                _fixed_bases.append(b.__source__)
                _inherit_templates.append(b)
            else:
                _fixed_bases.append(b)

        if len(_inherit_templates) > 1:
            raise TypeError("Cannot inherit from more than one template type.") from errors.configure(depth=1)

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
            cls = type.__new__(mcs, name, tuple(_fixed_bases), np, **kwargs)

        cls.__isfinal__ = False

        if name in mcs._fwrd_refs_registry:
            cls.register_forward_references(name)

        if len(_inherit_templates):
            mcs.__init__(cls, name, _fixed_bases, np, **kwargs)
            return TemplateType(cls, _inherit_templates[0].__argtypes__, {})  # type: ignore

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
        np = dict(cls.__dict__)
        for slot in np.get('__slots__', []):
            if slot in np:
                del np[slot]
        res = type(cls)(cls.__name__, cls.__bases__, np, **getattr(cls, "#kwargs", {}))
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
        cls = type.__new__(mcs, source.__name__, (), {'__module__': source.__module__, '_initialized': False})
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

        cls._initialized = True

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

    def __getattr__(cls, item):
        return getattr(cls.__source__, item)

    def __setattr__(cls, key, value):
        super(type(cls), cls).__setattr__(key, value)
        if not cls._initialized:  # the constructors must not trigger this behaviour
            return
        for ttype in cls._typecache.values():
            setattr(ttype, key, value)

    def __instancecheck__(cls, instance):
        other_type = type(instance)
        if not isinstance(other_type, MultiMeta):
            return False
        if other_type is cls.__source__:
            return True
        other_source = getattr(other_type, '__source__', object)
        return issubclass(other_source, cls.__source__)

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

    @property
    def __isfinal__(cls):
        return cls.__source__.__isfinal__

    @__isfinal__.setter
    def __isfinal__(cls, value):
        cls.__source__.__isfinal__ = value

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
        if type_check.parse(tparam, targ, raise_=False):
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

