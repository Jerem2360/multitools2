import collections.abc
import types
import typing


class _C(type): pass


_UnionType_Type = type(types.UnionType)  # this actually is <class 'type'>


frozendict = type(_C('_C', (), {}).__dict__)


ARGCOUNT_ERROR = 0b1  # (*argcount_range, n_given_args)
TYPE_ERROR = 0b10  # (expected, got)


EXPECTED_STR = "between {0} and {1}"

INCONSISTENT_NAMES = (
    '<module>',
)


GEN_LIST_LIKE = (list, set, frozenset)
GEN_MAPPING_LIKE = (dict, frozendict)
GEN_TYPE_LIKE = (type,)
GEN_TUPLE_LIKE = (tuple,)
GEN_UNION_LIKE = (types.UnionType, typing._BaseGenericAlias)  # , _UnionType_Type (this is 'type'!)


class Parser:
    def __init__(self, *mandatory, **optional):
        self.type_requirements = mandatory, list(optional.values())

    def parse(self, *args, **kwargs):
        """
        Recursively parse an argument list, checking them towards the types
        passed in on instantiation.
        Generics and Template types' arguments are also checked.
        """
        if not (len(args) or len(kwargs)):
            return 0, ()

        _a = list(args)
        _a.extend(kwargs.values())
        _args = tuple(_a)

        mandatory, optional = self.type_requirements

        if not (len(mandatory) <= len(args) <= len(mandatory) + len(optional)):
            return ARGCOUNT_ERROR, ((len(mandatory), len(mandatory) + len(optional)), str(len(args)))

        types = (*mandatory, *optional)

        for i in range(len(_args)):
            etype, eargs = self.parse_arg(_args[i], types[i])
            if etype:
                if i >= len(args):
                    try:
                        i = list(kwargs.keys())[i - len(args)]
                    except:
                        i = -1
                return etype, (*eargs, i)
        return 0, ()


    def parse_arg(self, arg, tp):
        if tp is None:
            if arg is not None:
                return TYPE_ERROR, (type(None), type(arg))
            return 0, ()

        if isinstance(tp, tuple):
            tp = typing.Union[tp]
        if isinstance(tp, (types.GenericAlias, types.UnionType, typing._BaseGenericAlias)):
            # print(type(tp), type(types.UnionType))
            if isinstance(tp, types.GenericAlias):
                origin = tp.__origin__
            else:
                origin = types.UnionType

            # print(tp, origin)

            if origin in GEN_LIST_LIKE:
                # noinspection PyTypeChecker
                for elem in arg:
                    subtype = tp.__args__[0]
                    etype, eargs = self.parse_arg(elem, subtype)
                    if etype:
                        return etype, (tp, origin[eargs[1]])
                return 0, ()

            if origin in GEN_MAPPING_LIKE:
                kt, vt = tp.__args__[:2]
                # noinspection PyTypeChecker
                for k, v in dict(arg).items():
                    etype, eargs = self.parse_arg(k, kt)
                    if etype:
                        return etype, (tp, origin[eargs[1], ...])
                    etype, eargs = self.parse_arg(v, vt)
                    if etype:
                        return etype, (tp, origin[..., eargs[1]])

            if origin in GEN_TYPE_LIKE:
                if not self.check_subclass(arg, tp.__args__[0]):
                    return TYPE_ERROR, (tp, origin[arg])

            if origin in GEN_TUPLE_LIKE:
                tp_reqs = tp.__args__
                # noinspection PyTypeChecker
                for i in range(len(arg)):
                    a = arg[i]
                    t = tp_reqs[i]
                    etype, eargs = self.parse_arg(a, t)
                    if etype:
                        return etype, (tp, origin[eargs[1]])

            if origin in GEN_UNION_LIKE:
                _types = tp.__args__
                # print(origin, origin in GEN_UNION_LIKE)
                for _tp in _types:
                    etype, eargs = self.parse_arg(arg, _tp)
                    if not etype:
                        return 0, ()

                return TYPE_ERROR, (tp, type(arg))

            return 0, ()

        # print('x', tp)
        if not isinstance(arg, tp):
            if isinstance(tp, tuple):
                tp = typing.Union[tp]
            return TYPE_ERROR, (tp, type(arg))

        return 0, ()

    @classmethod
    def check_subclass(cls, clas, subclass):
        if isinstance(subclass, types.UnionType):
            res = False
            for c in subclass.__args__:
                res |= cls.check_subclass(clas, c)

            return res
        return issubclass(clas, subclass)

    @classmethod
    def build_error(cls, etype, eargs, fname=None):
        if etype & ARGCOUNT_ERROR:
            range_, size = eargs

            if (range_.start, range_.step) == (0, 1):
                msg = f"no more than {range_.stop - 1} arguments"
            elif range_.start + 1 == range_.stop:
                msg = f"exactly {range_.start} arguments"
            elif range_.step == 1:
                msg = f"between {range_.start} and {range_.stop - 1} arguments"
            else:
                msg = f"{range_.start}:{range_.stop}:{range_.step} arguments"

            plural = 'were' if size > 1 else 'was'
            msg += f", but {size} {plural} given."
            prefix = "Expected " if fname is None else f"'{fname}' expects "

            return TypeError(prefix + msg)
        if etype & TYPE_ERROR:
            name1 = eargs[0].__name__ if (not isinstance(eargs[0], types.GenericAlias)) and isinstance(eargs[0], type) else repr(eargs[0])
            name2 = eargs[1].__name__ if (not isinstance(eargs[1], types.GenericAlias)) and isinstance(eargs[1], type) else repr(eargs[1])
            pref1 = ('' if fname is None else f"'{fname}'")
            pref2 = ('' if (len(eargs) <= 2) or (eargs[2] < 0) else f", argument {eargs[2]}: ")
            return TypeError(pref1 + pref2 + f"Expected type '{name1}', got '{name2}' instead.")


class ErrorInformation:
    """
    Information on why code execution terminated.

    If no error occurs, use ErrorInformation.SUCCESS ; otherwise,
    call this class with the following information about the exception:

    - etype is an integer constant indicating the type of the exception

    - eargs are specifications to the exception type. The format varies
        depending on the exception type.
    """
    def __init__(self, etype=None, eargs=None, fname=None):
        self.name = fname
        self.error = None if None in (etype, eargs) else etype, eargs
        if not etype:
            self.error = None
            self.name = None

    def __bool__(self):
        """
        bool(exception_information) -> whether this is a normal termination
        """
        return self.error is None

    def build(self):
        """
        Convert the exception information into a raisable exception.
        """
        return Parser.build_error(*self.error, fname=self.name)

    def __repr__(self):
        if self:
            return f"ErrorInformation.SUCCESS"
        return f"ErrorInformation{self.error}"

    SUCCESS: 'ErrorInformation' = ...
    """Normal termination"""


ErrorInformation.SUCCESS = ErrorInformation()


def parse(*args, raise_=True, depth=1, fname=None):
    """
    parse(*types, *arguments, raise_=True, depth=1)

    Parse a set of arguments given a set of types.
    First pass in the types to which to compare the arguments,
    and then pass in the arguments themselves.
    There must be the same number of types and arguments.

    raise_ decides whether to raise an exception if arguments are incompatible
    with types.

    _depth defines the depth in the call stack (from the caller's point of view)
    at which to raise the exception. Default is 1. If raise_ is False, this is ignored.
    """
    # to avoid circular import problems:
    from . import runtime
    from . import errors

    # parse our own arguments:
    if not len(args):
        raise TypeError("'parse' takes at least two positional arguments.")
    if len(args) % 2:
        raise TypeError(f"'parse' takes an even number of positional arguments, but {len(args)} were given.")
    nargs = int(len(args) / 2)

    _types = args[:nargs]
    _args = args[nargs:]

    # make sure our depth is in range of the call stack:
    if depth < 0:
        depth = 0
    depth += 1
    if depth >= len(runtime.call_stack):
        depth = len(runtime.call_stack) - 1

    # print(_types, _args)
    # do the parsing:
    parser = Parser(*_types)
    etype, eargs = parser.parse(*_args)

    # if possible, get the name of the callable from which this was invoked.
    # inconsistent names like '<module>' are ignored.
    fname_d = fname
    f = None
    if depth == 1:
        if len(runtime.call_stack) > 2:
            f = runtime.call_stack[1]
    else:
        f = runtime.call_stack[depth - 1]
        if f.f_code.co_name in INCONSISTENT_NAMES:
            f = None
    fname = fname_d if f is None else f.f_code.co_name

    # raise the potential exception:
    if etype:
        if raise_:
            raise Parser.build_error(etype, eargs, fname=fname) from errors.configure(depth=depth)
        return ErrorInformation(etype, eargs, fname=fname)
    return ErrorInformation.SUCCESS


def islen(arglist, range_, raise_=True, depth=1):
    """
    Check for the number of the given arguments.
    Checking towards slices or range objects allows more
    control over the accepted number of arguments.

    raise_ decides whether to raise an exception when a wrong number of
    arguments is encountered.

    depth defines the depth in the call stack (from the caller's point of view)
    at which to raise the exception. Default is 1. If raise_ is False, this is ignored.
    """
    parse(tuple, range | slice | int, arglist, range_)

    from . import runtime
    from . import errors

    if isinstance(range_, int):
        range_ = range(range_, range_ + 1)
    if isinstance(range_, slice):
        range_ = range(range_.start, range_.stop, range_.step)

    # make sure our depth is in range of the call stack:
    if depth < 0:
        depth = 0
    depth += 1
    if depth >= len(runtime.call_stack):
        depth = len(runtime.call_stack) - 1

    # if possible, get the name of the callable from which this was invoked.
    # inconsistent names like '<module>' are ignored.
    f = None
    if depth == 1:
        if len(runtime.call_stack) > 2:
            f = runtime.call_stack[1]
    else:
        f = runtime.call_stack[depth - 1]
        if f.f_code.co_name in INCONSISTENT_NAMES:
            f = None
    fname = None if f is None else f.f_code.co_name

    # raise the potential exception:
    size = len(arglist)
    if size not in range_:
        if raise_:
            raise Parser.build_error(ARGCOUNT_ERROR, (range_, size), fname=fname) from errors.configure(depth=depth)
        return ErrorInformation(ARGCOUNT_ERROR, (range_.start, range_.stop - 1, size), fname=fname)
    return ErrorInformation.SUCCESS

