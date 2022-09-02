

__all__ = [
    "parse_args",
]


import types
import typing
from collections import abc

### -------- Imports -------- ###

from ._typeshed import *
from ._meta import *
from .errors._errors import *
from . import _singleton


# debugging setup:
from ._startup._debug import debugger

DEBUGGER = debugger("TYPE_CHECK/debug")


# invalid argument singleton:
@_singleton.Singleton
class InvalidArg: ...


### -------- Constants -------- ###
__GENERIC_CHECK__ = '__generic_check__'
__ORIGIN__ = '__origin__'

cast_types = {
    int: '__int__',
    bytes: '__bytes__',
    float: '__float__',
    bool: '__bool__',
    complex: '__complex__'
}


### -------- Functions -------- ###


def parse_args(args, *types, depth=0):
    """
    Parse args and type-check them against types.
    Raises TypeError if an arg is of the wrong type,
    and ValueError if an argument to this function
    is incorrect.
    TypeError is raised at the given depth in the call stack,
    which defaults to zero.
    """
    if len(args) != len(types):
        raise err_depth(TypeError, "There must be as much types a arguments.", depth=1)

    if not isinstance(depth, int):
        raise err_depth(TypeError, TYPE_ERR_STR.format('int', type(depth).__name__), depth=1)
    if depth < 0:
        raise err_depth(ValueError, "Depth cannot be negative.", depth=1)

    valid_args = []
    for i in range(len(args)):
        arg, tp = args[i], types[i]

        if tp is Ellipsis:
            raise err_depth(TypeError, "This function does not support Ellipsis.", depth=1)

        valid_arg, expected, got = _parse_one_arg(arg, tp)
        if valid_arg is InvalidArg:
            if got is Ellipsis:  # cannot typecheck against a non-type object.
                raise err_depth(ValueError, f"Cannot type-check against non-type object {expected}.", depth=1)
            if expected is Ellipsis:  # invalid generic type
                raise err_depth(ValueError, f"Invalid Generic type '{got}' for type check.", depth=1)
            raise err_depth(TypeError, TYPE_ERR_STR.format(expected, got), depth=depth+1)
        valid_args.append(valid_arg)

    return tuple(valid_args)


def _parse_one_arg(arg, tp):
    """_parse_one_arg(arg, type) -> valid_args, expected, got"""
    if isinstance(tp, types.GenericAlias):
        if not isinstance(arg, tp.__origin__):
            return InvalidArg, tp.__origin__.__name__, type(arg).__name__
        valid, expected, got = None, None, None
        if tp.__origin__ is list:
            # noinspection PyTypeChecker
            valid, expected, got = _parse_list(arg, tp.__args__)
        if tp.__origin__ is tuple:
            # noinspection PyTypeChecker
            valid, expected, got = _parse_tuple(arg, tp.__args__)
        if tp.__origin__ is dict:
            # noinspection PyTypeChecker
            valid, expected, got = _parse_dict(arg, tp.__args__)
        if tp.__origin__ is abc.Callable:
            valid, expected, got = _parse_callable(arg)
        if isinstance(tp, types.UnionType):
            valid, expected, got = _parse_one_arg(arg, tp.__args__)

        if None in (valid, expected, got):
            return InvalidArg, Ellipsis, tp.__origin__.__name__  # this means invalid generic / template type

        return valid, expected, got

    if isinstance(tp, MultiMeta):
        expected = tp.__name__
        got = type(arg).__name__

        if hasattr(tp, __ORIGIN__):  # tp is a template type
            arg_t = type(arg)
            if not isinstance(arg, (tp.__origin__, tp)) or not hasattr(arg_t, __ORIGIN__):
                valid = InvalidArg
            else:
                valid = arg if tp.__args__ == arg_t.__args__ else InvalidArg

        else:
            DEBUGGER.print("Parser: checking", arg, "against type", tp, "isinstance =", isinstance(arg, tp))
            valid = arg if isinstance(arg, tp) else InvalidArg

        return valid, expected, got

    if isinstance(tp, (tuple, list)):
        valid_arg = arg
        expected = []
        got = type(arg).__name__

        do_check = True
        for t in tp:
            valid, exp, _got = _parse_one_arg(arg, t)
            if '|' in exp:
                exp = f"({exp})"
            expected.append(exp)
            got = _got
            if do_check:
                if valid is InvalidArg:
                    valid_arg = valid
                    do_check = False

        exp_str = ' | '.join(expected) if len(expected) > 0 else 'Any'
        return valid_arg, exp_str, got

    if isinstance(tp, type):
        expected = tp.__name__
        got = type(arg).__name__
        DEBUGGER.print("Parser: parsing ", arg, "isinstance =", isinstance(arg, tp))
        valid = InvalidArg if not isinstance(arg, tp) else arg
        return valid, expected, got

    return InvalidArg, repr(tp), Ellipsis  # tp cannot be type-checked against


def _parse_list(list_obj, args):
    """_parse_XXX(obj, args) -> valid_args, expected, got"""
    # DEBUGGER.print("List: parsing ", list_obj)
    valid_args = []
    expected = 'Any'
    got = []
    for x in list_obj:
        valid, exp, _got = _parse_one_arg(x, args[0])
        # DEBUGGER.print("List: valid, expected, got =", (valid, exp, _got))
        valid_args.append(valid)
        expected = exp
        got.append(_got)

    exp_str = f"list[{expected}]"
    if InvalidArg in valid_args:
        return InvalidArg, exp_str, f"list[{' | '.join(got)} | ...]"
    return valid_args, exp_str, f"list[{' | '.join(got)}]"


def _parse_tuple(tuple_obj, args):
    """_parse_XXX(obj, args) -> valid_args, expected, got"""
    valid_args = []
    expected = f"tuple[{', '.join((arg.__name__ if arg is not Ellipsis else '...') for arg in args)}]"
    got = []
    if len(args) == 0:
        return InvalidArg, expected, 'tuple[]'
    if args[-1] is not Ellipsis:
        if len(args) != len(tuple_obj):
            return InvalidArg, expected, f"tuple[{', '.join(type(x).__name__ for x in tuple_obj)}]"

    do_check = True
    for i in range(len(tuple_obj)):
        x = tuple_obj[i]
        if do_check:
            t_x = args[i]
        else:
            valid_args.append(x)
            got.append(type(x).__name__)
            continue

        if t_x is Ellipsis:
            do_check = False
            valid_args.append(x)
            got.append(type(x).__name__)
            continue

        valid, _, got_ = _parse_one_arg(x, t_x)
        got.append(got_)
        valid_args.append(valid)

    got_str = ', '.join(got)
    return (InvalidArg if InvalidArg in valid_args else valid_args), expected, got_str


def _parse_dict(dict_obj, args):
    """_parse_XXX(obj, args) -> valid_args, expected, got"""
    if len(args) != 2:
        return dict_obj, 'dict', 'dict'

    expected = f"dict[{args[0].__name__}, {args[1].__name__}]"
    keys_valid = []
    values_valid = []
    kv_got = ['Any', 'Any']

    for k, v in dict_obj.items():
        k_t, v_t = args
        k_valid, k_e, k_got = (_parse_one_arg(k, k_t)) if k_t is not Ellipsis else (k, '...', type(k).__name__)
        v_valid, v_e, v_got = (_parse_one_arg(v, v_t)) if v_t is not Ellipsis else (v, '...', type(v).__name__)
        DEBUGGER.print(k_valid, v_valid)
        keys_valid.append(k_valid)
        values_valid.append(v_valid)
        kv_got = [k_got, v_got]

    DEBUGGER.print("dict: keys_valid =", keys_valid)
    DEBUGGER.print("dict: values_valid =", values_valid)

    if (InvalidArg in keys_valid) and (InvalidArg in values_valid):
        return InvalidArg, expected, f"dict[{kv_got[0]} | ..., {kv_got[1]} | ...]"
    if InvalidArg in keys_valid:
        return InvalidArg, expected, f"dict[{kv_got[0]} | ..., {kv_got[1]}]"
    if InvalidArg in values_valid:
        return InvalidArg, expected, f"dict[{kv_got[0]}, {kv_got[1]} | ...]"

    got_str = f"dict[{kv_got[0]}, {kv_got[1]}]"
    return dict_obj, expected, got_str


def _parse_callable(obj):
    # no check for the argument and return types are done, only callable(obj) is checked.
    if callable(obj):
        return obj, 'Callable[[...], Any]', type(obj).__name__
    return InvalidArg, 'Callable[[...], Any]', type(obj).__name__


"""
# functions:
def parse_arguments(arguments, *types, depth=0):
    ""
    A simple argument parsing primitive that type-check and tries to
    do type-conversions to the valid types.

    This function takes given arguments and types, and compares them.
    If the argument is of the right type, it is yielded directly.
    If it can be converted to the right type using a magic method,
    the conversion is made and its result is yielded.
    Otherwise, a TypeError of the given depth is raised.

    Note that if Generic aliases are used and provide methods
    to do an exact check, these methods are called to do so.
    Default implementations for generic checking exist in
    the tuple[T, ...], list[T] and dict[KT, VT] generics.
    If no methods are provided, assume we have the right
    value.
    ""
    valid_args = []
    for i in range(len(types)):
        arg_val = InvalidArg
        try:
            arg = arguments[i]
        except KeyError or IndexError:
            raise err_depth(ValueError, "The same number of arguments as types must be specified.", depth=1)
        tp = types[i]

        if tp in (Ellipsis, type(Ellipsis)):
            raise err_depth(TypeError, "Ellipsis is not supported by this function.", depth=1)

        if isinstance(tp, (tuple, list)):
            typename = ''
            for t in tp:
                if tp in (Ellipsis, type(Ellipsis)):
                    raise err_depth(TypeError, "Ellipsis is not supported by this function.", depth=1)

                if not isinstance(t, (type, type(None))):
                    raise err_depth(TypeError, TYPE_ERR_STR.format('type | None', type(tp).__name__), depth=1)
                if t is None:
                    t = type(None)
                arg_val_temp = _parse_one_arg(arg, t)
                if arg_val_temp is not InvalidArg:
                    arg_val = arg_val_temp
                typename += t.__name__
                typename += ' | '
            typename = typename.removesuffix(' | ')

        elif isinstance(tp, type):
            arg_val_temp = _parse_one_arg(arg, tp)
            if arg_val_temp is not InvalidArg:  # no need to override a valid value with an invalid one.
                arg_val = arg_val_temp
            typename = tp.__name__

        else:
            raise err_depth(TypeError, TYPE_ERR_STR.format('type | tuple[type, ...]', type(tp).__name__), depth=1)

        if arg_val is InvalidArg:
            raise err_depth(TypeError, TYPE_ERR_STR.format(typename, type(arg).__name__), depth=depth+1)

        valid_args.append(arg_val)

    return valid_args


def _parse_one_arg(arg, tp):
    # print(repr(arg), tp)

    if tp in (Ellipsis, type(Ellipsis)):
        raise err_depth(TypeError, "Ellipsis is not supported by this function.", depth=2)

    try:
        if isinstance(arg, tp):
            return _check_generic(arg, tp)
    except TypeError:
        if isinstance(arg, tp.__origin__):
            return _check_generic(arg, tp)

    if tp in cast_types:
        if not hasattr(arg, cast_types[tp]):
            return InvalidArg
        # print('cast function is', cast_types[tp])
        cast_f = getattr(arg, cast_types[tp])
        return _check_generic(cast_f(), tp)

    DEBUGGER.print('not an instance:', tp)
    return InvalidArg


def _check_generic(arg, gen):
    # noinspection PyUnresolvedReferences
    if not (isinstance(gen, types.GenericAlias) or (typing.Generic in gen.__bases__)) and not (isinstance(gen, MultiMeta) and gen.is_generic()):
        # DEBUGGER.print('not generic:', gen)
        # DEBUGGER.print(type(gen))
        return arg

    if not isinstance(gen, MultiMeta):
        if gen.__origin__ is list:
            list_t = gen.__args__[0]
            for x in arg:
                if not isinstance(x, list_t):
                    return InvalidArg

        if gen.__origin__ is tuple:
            tuple_ts = gen.__args__
            for i in range(len(tuple_ts)):
                if tuple_ts[i] is Ellipsis:
                    break
                elem, tp = arg[i], tuple_ts[i]
                if tp is None:
                    tp = type(None)
                if (tp in cast_types) and hasattr(elem, cast_types[tp]):
                    cast_f = getattr(elem, cast_types[tp])
                    arg[i] = _check_generic(cast_f(), tp)
            return arg
    
        if gen.__origin__ is dict:
            pair_t = gen.__args__
            for k, v in arg.items():
                if (pair_t[0] is not Ellipsis) and not isinstance(k, pair_t[0]):
                    if (pair_t[0] in cast_types) and hasattr(k, cast_types[pair_t[0]]):
                        cast_f = getattr(k, cast_types[pair_t[0]])
                        return _check_generic(cast_f(), pair_t[0])

                if (pair_t[1] is not Ellipsis) and not isinstance(v, pair_t[1]):
                    if (pair_t[1] in cast_types) and hasattr(v, cast_types[pair_t[1]]):
                        cast_f = getattr(v, cast_types[pair_t[1]])
                        return _check_generic(cast_f(), pair_t[1])

        return arg

    if hasattr(gen, __GENERIC_CHECK__):
        valid = gen.__generic_check__(arg)
        return arg if valid else InvalidArg

    if hasattr(gen, __ORIGIN__):
        if not isinstance(type(arg), MultiMeta):
            return InvalidArg
        if not hasattr(type(arg), __ORIGIN__):
            return InvalidArg
        if type(arg).__origin__ is not gen.__origin__:
            return InvalidArg
        if type(arg).__args__ != gen.__args__:
            return InvalidArg
        return arg

    return arg if isinstance(arg, gen) else InvalidArg

"""

