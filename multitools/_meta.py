"""
Common base metaclass for all types of this library.
"""


__all__ = [
    "MultiMeta",
    "reversed_friendship",
    "generic",
    "abstractmethod",
]


### -------- Imports -------- ###
import sys
import copy

from ._startup._debug import debugger
from . import *
from .errors._errors import *
from ._tools import Decorator

# debuggers:
_D_MULTIMETA = debugger("MULTIMETA/debug")
_D_COPY = debugger("COPY/debug")


### -------- Constants -------- ###
__FRIENDS__ = '__friends__'
__DICT__ = '__dict__'
__WEAKREF__ = '__weakref__'
__TEMPLATE__ = '__template__'
__ORIGIN__ = '__origin__'
__SUBCLASSHOOK__ = '__subclasshook__'
__INSTANCEHOOK__ = '__instancehook__'
__ISABSTRACTMETHOD__ = '__isabstractmethod__'
__ISABSTRACT__ = '__isabstract__'
__ABSTRACT__ = '__abstract__'
__REVERSED__ = '@MultiMeta/friendship/reversed'
__CREATION__ = '@MultiMeta/creation'


### -------- Decorators -------- ###

def reversed_friendship(cls):
    """
    Invert the friendship behaviour of a class.
    Instead of acting as a subclass of its friends,
    it will act as a parent class of its friends.
    """
    debugger.audit(f'{_LIB_NAME}.<meta>.reversed_friendship', cls)
    setattr(cls, __REVERSED__, True)
    return cls


@Decorator
def generic(cls, *types):
    """
    Allow a type to be generic and support template arguments,
    a bit like for typing.Generic. The main difference is that
    template arguments are runtime type-checked towards the
    decorator's arguments, which must be types. Template arguments
    can also be implemented by defining a __template__ class method
    that takes the template arguments as parameters.
    If no arguments are passed, this decorator does nothing.

    For example:

    @generic(type1, type2, ...)
    class C(metaclass=MultiMeta):
        def __template__(cls, arg1: type1, arg2: type2, ...):
            res = cls.copy(cls)
            # do stuff
            return res

    C[arg1, arg2, ...] -> generic 'C' with arguments arg1, arg2, ...

    Note that template types are cached, so __template__ will
    be called only once for each distinct set of template arguments.
    """
    if not _typecheck_template_type(types):
        raise err_depth(TypeError, TYPE_ERR_STR.format('type | tuple[type, ...]', type(types).__name__), depth=2)
    if not isinstance(cls, type):
        # here depth is 2 because our function will be called by Decorator.__call__.<_inner>, adding a layer to the call stack.
        raise err_depth(TypeError, TYPE_ERR_STR.format('type', type(cls).__name__), depth=2)

    if len(types) > 0:
        cls.__generic__ = types
        _D_MULTIMETA.print(f"Changed __generic__ of type '{cls.__name__}' to {types}.")
        debugger.audit(f"{_LIB_NAME}.generic", *types)
    return cls


def abstractmethod(func):
    func.__isabstractmethod__ = True
    return func


### -------- Abstract method / field descriptors -------- ###


class _AbstractField:
    def __init__(self):
        self.__isabstract__ = True

    def __get__(self, instance, owner):
        raise err_depth(TypeError, "Abstract field.", depth=1)

    def __set__(self, instance, value):
        raise err_depth(TypeError, "Abstract field.", depth=1)


class _AbstractMethod:
    def __init__(self, func):
        """
        Type representing bound abstract methods of types.
        """
        self._allow_instance_get = True
        self._allow_class_get = True
        if isinstance(func, (Function, Method)):
            self.__func__ = _func_without_code(func)
        if isinstance(func, classmethod):
            # noinspection PyTypeChecker
            self.__func__ = classmethod(_func_without_code(func.__func__))
        if isinstance(func, staticmethod):
            # noinspection PyTypeChecker
            self.__func__ = staticmethod(_func_without_code(func.__func__))
        if isinstance(func, property):
            # noinspection PyTypeChecker
            self.__func__ = property(
                _func_without_code(func.fget),
                _func_without_code(func.fset),
                _func_without_code(func.fdel),
                func.__doc__
            )
            self._allow_class_get = False
            self._allow_instance_get = False

        self._source = func
        self.__code__ = None

    def __get__(self, instance, owner):
        if instance is not None:
            if not self._allow_instance_get:
                raise err_depth(TypeError, "Abstract method / field.", depth=1)
            self.__self__ = instance
        if not self._allow_class_get:
            raise err_depth(TypeError, "Abstract method / field.", depth=1)
        return self

    def __call__(self, *args, **kwargs):
        if not callable(self._source):
            raise err_depth(TypeError, NOT_CALLABLE_ERR_STR.format(type(self._source).__name__), depth=1)
        raise err_depth(TypeError, "Abstract method / field.", depth=1)

    def __getattr__(self, item):
        if hasattr(self.__func__, item):
            return getattr(self.__func__, item)
        raise err_depth(AttributeError, ATTR_ERR_STR.format(self.__class__.__name__, item), depth=1)


### -------- MultiMeta -------- ###

class MultiMeta(type):
    """
    Common metatype for all classes from the multitools library.
    It supports abstract classes, methods, attributes and fields,
    copy and deepcopy, as well as a special functionality called
    class friends. Generic types are also supported.

    ### ------ Class friendship ------ ###

    If a type or class has one or more friends, it will, upon
    instance check, act as subclasses of its friends, i.e. the
    type's instances will be considered instances of its friend types.
    If the @reversed_friendship decorator is used, this behaviour is
    inverted as described in the decorator's doc.

    Friendship is held by the '__friends__' field of MultiMeta types.
    Specifying friends for a class requires a specific syntax.

    For example:

    class C(metaclass=MultiMeta):
        __friends__ = int

    Here, class C 's friend is the int type. To specify multiple friend types,
    the __friends__ field should be assigned to a tuple of the wanted types,
    such as:
        __friends__ = int, complex, bool

    Now, class C 's friends will be the int, complex and bool types.

    By default, friendship is not inherited through subclassing.
    To fetch the friends of the parent class, use '...' (Ellipsis).

    For example:

    class B(metaclass=MultiMeta):
        __friends__ = int, float


    class C(B):
        __friends__ = ...


    Here, class C 's friends will be the friends of its parent class, B.
    This means class C has now 2 friend classes: the int and float types,
    friends that were fetched from the parent class B, without the need
    to reassign them explicitly.

    It is also possible to fetch the friends of the parent class, whilst
    at the same time adding our own friends to the class. This is done as
    follows:

    class B(metaclass=MultiMeta):
        __friends__ = str, bool

    class C(B):
        __friends__ = ..., float, tuple


    Here, class C 's friends are types str and bool, fetched from the parent
    class, as well as types float and tuple, directly following the '...' in
    the assignment.

    If the __friends__ field is not specified in a class' body, the class won't
    have any friends. If a type is found multiple times in the same class'
    __friends__ field, only one is kept. This means that each type is guaranteed
    to appear at most once in the __friends__ field, when reading it from
    outside the class body.

    Note that friendship can only be set from inside a class' body. In other
    circumstances, this field is read-only and exposed as a tuple listing
    all the class' friend types. These are all guaranteed to be type objects.


    ### ------ Generic types ------ ###

    A generic or template type is a type that supports template arguments through
    subscription. Passing in template arguments to a type works very similarly as
    in the C++ or Carbon languages. The syntax is the following:

    type[arg1, arg2, ...] passes the tuple (arg1, arg2, ...) as template arguments
    to the given type.
    This syntax is equivalent to 'type<arg1, arg2, ...>' in C++.
    Note that template arguments are runtime type-checked, as opposed to those passed
    in to typing.Generic. This will be discussed later.

    To be able to process template arguments, a type must accept some.
    It can also implement its own way of processing template arguments.

    In order to accept such arguments, a type must be decorated with the
    @generic() decorator and pass in the types of the accepted template arguments.

    For example:

    @generic(type, type)
    class C(metaclass=MultiMeta): pass

    Here, class 'C' accepts two template arguments of type 'type'.
    Therefore,
    C[str, bytes] is valid
    C[10] ; C['hello'] ; C[int] are invalid.

    '...' means a template argument can be of any type. For instance,
    @generic(int, ..., float)
    class C(metaclass=MultiMeta): pass
    would accept 3 template arguments - an integer, whatever object, and a floating point number.

    As explained earlier, types can also implement their own way of processing
    template arguments, by defining the __template__ class method. It should accept
    the appropriate template arguments as parameters, and return a copy of the type,
    that can be changed as needed.
    To copy the class, use the copy_shallow and copy_deep class methods.
    copy.copy and copy.deepcopy can also be used to copy the class.
    For more info, refer to their respective documentations.

    Note that __template__ is called only once for each different template argument
    combination: for performance and coherence purposes, template types are cached.
    """
    def __new__(mcs, name, bases, np, generic=None, friends=None, **kwargs):
        """
        Create and return a new type object.
        The 'friends' parameter allows specifying class friendship for types
        created by calling the metaclass.
        The 'generic' can specify the type of template arguments the type accepts.
        The @generic(...) decorator does the same.
        """
        debugger.audit(f'{_LIB_NAME}.MultiMeta.__new__', name, bases, np)

        _abs = False
        abs_attrs = []
        _abstract_base = []
        for b in bases:
            abstract = getattr(b, __ABSTRACT__, False)
            if abstract:
                for elem in b.__abstracts__:
                    _abstract_base.append(b.__name__ + '.' + elem)

        for elem in _abstract_base:
            cls, name = elem.split('.')
            if name not in np:
                abs_attrs.append(name)
                _abs = True

        for k, v in np.items():
            if v is Ellipsis:
                np[k] = _AbstractField()

        cls = super().__new__(mcs, name, bases, np)
        setattr(cls, __CREATION__, True)
        if not kwargs.get('_copy', False):
            _D_MULTIMETA.print(f"creating MultiMeta class '{name}' ...")
        else:
            _D_MULTIMETA.print(f"copying MultiMeta class '{name}' ...")

        cls.__exporter__ = _get_exporter(cls)
        _D_MULTIMETA.print(f"-> exporter is <module '{cls.__exporter__}'>.")

        cls.__generic__ = () if generic is None else generic  # template parameter types. Empty by default.
        _D_MULTIMETA.print(f"-> generic: {cls.__generic__}.")

        cls._typecache = {}

        setattr(cls, __REVERSED__, False)

        base = cls.mro()[1]  # __mro__ = (cls, base, base.__base__, ...)

        # friendship management:
        if friends is None:
            friends = np.get(__FRIENDS__, ())
            if friends is Ellipsis:
                cls.__friends__ = _check_friends(getattr(base, __FRIENDS__, ()))
            elif isinstance(friends, tuple):
                if (len(friends) > 1) and (friends[0] is Ellipsis):
                    cls.__friends__ = _check_friends((*getattr(base, __FRIENDS__, ()), *friends[1:]))
                else:
                    cls.__friends__ = _check_friends(friends)
            elif isinstance(friends, type):
                cls.__friends__ = (friends,)
            else:
                # user specified an invalid value for friends:
                raise err_depth(SyntaxError, 'Wrong syntax for class friendship (\'__friends__\'). See documentation for more info.', depth=1)

        else:
            if not isinstance(friends, (tuple, type)):
                raise err_depth(TypeError, TYPE_ERR_STR.format('tuple[type] | type', type(friends).__name__), depth=1)

            if isinstance(friends, type):
                friends = (friends,)
            for f in friends:
                if not isinstance(f, type):
                    raise err_depth(TypeError, TYPE_ERR_STR.format('tuple[type] | type', f"tuple[{type(f).__name__}, ...]"), depth=1)

            cls.__friends__ = _check_friends(friends)

        _D_MULTIMETA.print(f"-> friends are {cls.__friends__}.")

        cls.__abstract__ = False
        cls.__abstracts__ = abs_attrs

        for k, v in cls.__dict__.items():
            if getattr(v, __ISABSTRACTMETHOD__, False):
                cls.__abstract__ = True
                cls.__abstracts__.append(k)
                if not isinstance(v, _AbstractMethod):
                    setattr(cls, k, _AbstractMethod(v))
            elif getattr(v, __ISABSTRACT__, False):
                cls.__abstract__ = True
                cls.__abstracts__.append(k)
                if not isinstance(v, _AbstractField):
                    setattr(cls, k, _AbstractField())

        cls.__abstract__ = _abs or cls.__abstract__
        setattr(cls, __CREATION__, False)

        return cls

    def __setattr__(cls, key, value):
        """
        Implement setattr(cls, key, value)
        Disallow modifying read-only fields.
        """
        is_creating = getattr(cls, __CREATION__, False)
        if (key == __FRIENDS__) and not is_creating:
            raise err_depth(AttributeError, "read-only attribute.", depth=1)
        return super().__setattr__(key, value)

    def __init_subclass__(mcs, **kwargs):
        """
        Make sure MultiMeta subclasses get registered into
        copy dispatches too.
        """
        _D_MULTIMETA.print(f"registering '{mcs.__name__}' MultiMeta subclass.")
        mcs._register_copy_dispatches()

    def __copy__(cls):
        """
        Implement copy.copy(cls)
        """
        _D_COPY.print("running 'copy'...")
        return type(cls)(cls.__name__, cls.__bases__, dict(cls.__dict__).copy(), generic=cls.__generic__, _copy=True)

    def __deepcopy__(cls, memodict={}):
        """
        Implement copy.deepcopy(cls, memodict={})
        Normally, metatypes' copy callbacks are ignored, except
        for MultiMeta and its subclasses. This is made possible by the internal
        _register_copy_dispatches() helper function.
        """
        _D_COPY.print(f"running 'deepcopy'...")
        np = {}
        for k, v in cls.__dict__.items():
            if not k.startswith(('@', '#')):  # hide special attributes that pollute debugging.
                _D_COPY.print(f'(dict scan) Copying value of type {type(v).__name__} under key {repr(k)}.')
            if k in (__DICT__, __WEAKREF__):  # never copy these attributes
                continue
            try:
                np[k] = copy.deepcopy(v)
            except:
                raise err_depth(TypeError, f"'{type(v)}' object cannot be copied.", depth=1)
        return type(cls)(
            copy.deepcopy(cls.__name__, memo=memodict),
            cls.__bases__,
            np,
            generic=copy.deepcopy(cls.__generic__, memo=memodict),
            _copy=True
        )

    def __getitem__(cls, item):
        """
        Implement cls[*args]

        This first looks for the template args inside the type's typecache, and
        if the args are found, return the type associated with it, avoiding the re-creation
        of a new type each time __getitem__ is called.
        If the type doesn't already exist, call the __template__ callback, assuming
        it returns a copy of the original type, changed in any needed way.
        Finally, this copy is stored into the type cache for the first step of
        the next __getitem__ call.
        __template__ can either be implemented in the metaclass or in the class itself (using @classmethod).

        Note: each generic (template) type stores its template arguments inside its
        __args__ and __parameters__ attributes, in the same way as for typing.Generic.
        """
        if len(cls.__generic__) == 0:
            return cls

        args = (item,) if not isinstance(item, tuple) else item
        if len(args) != len(cls.__generic__):
            raise err_depth(TypeError, POS_ARGCOUNT_ERR_STR.format(f"{cls.__name__}[]", len(cls.__generic__), len(args)), depth=1)

        if args in cls._typecache:
            return cls._typecache[args]

        for i in range(len(args)):
            if cls.__generic__[i] is Ellipsis:
                continue
            if not _typecheck_template(args[i], cls.__generic__[i]):
                expected = ' | '.join(t.__name__ for t in cls.__generic__[i]) if isinstance(cls.__generic__[i], tuple) else cls.__generic__[i].__name__
                raise err_depth(TypeError, TYPE_ERR_STR.format(cls.__generic__[i].__name__, type(args[i]).__name__), depth=1)

        # noinspection PyTypeChecker
        template_func = getattr(cls, __TEMPLATE__, classmethod(lambda c, *args: c.dup_shallow()).__get__(None, cls))
        res = template_func(*args)

        if not isinstance(res, MultiMeta):
            raise err_depth(TypeError, "__template__ must return a MultiMeta instance.", depth=1)

        res.__origin__ = cls
        res.__args__ = args

        params = []
        for arg in res.__args__:
            if arg not in params:
                params.append(arg)
        res.__parameters__ = tuple(params)

        res.__generic__ = ()
        argnames = ', '.join(_build_template_list_repr(args))
        res.__name__ += f"[{argnames}]"
        res.__qualname__ = res.__name__
        cls._typecache[args] = res
        return res

    def __instancecheck__(cls, instance):
        if hasattr(cls, __INSTANCEHOOK__):
            # noinspection PyUnresolvedReferences
            res = cls.__instancehook__(instance)
            if res is not NotImplemented:
                return super().__instancecheck__(instance)

        if not hasattr(cls, __ORIGIN__):
            return False
        # noinspection PyUnresolvedReferences
        return isinstance(instance, cls.__origin__)

    def __eq__(cls, other):
        if hasattr(cls, __ORIGIN__):
            # noinspection PyUnresolvedReferences
            return (cls.__args__ == other.__args__) and (cls.__origin__ == other.__origin__)
        return super().__eq__(other)

    def __subclasscheck__(cls, subclass):
        if hasattr(cls, __SUBCLASSHOOK__):
            # noinspection PyUnresolvedReferences
            res = cls.__subclasshook__(subclass)
            if res is not NotImplemented:
                return res
        return super().__subclasscheck__(subclass)

    def __call__(cls, *args, **kwargs):
        if cls.__abstract__:
            raise err_depth(TypeError, "Abstract type.", depth=1)
        return super().__call__(*args, **kwargs)

    def dup_shallow(cls):
        """
        Duplicate a type using shallow copy.
        Useful to implement the __template__ callback.
        """
        return copy.copy(cls)

    def dup_deep(cls):
        """
        Duplicate a type using deep copy.
        Useful to implement the __template__ callback.
        """
        return copy.deepcopy(cls)

    def is_generic(cls):
        """
        Return whether the type is Generic (in the conventions of the
        typing module). This includes types that accept template
        arguments and ones that are the result of passing template
        arguments to their origin.
        """
        return (cls.__generic__ != ()) or hasattr(cls, __ORIGIN__)

    @classmethod
    def _register_copy_dispatches(mcs):
        """
        Internal helper function to allow MultiMeta and its subclasses' __copy__ and
        __deepcopy__ methods to be called by the copy module.
        This makes true deepcopy possible on type objects.
        This actually adds the metatype to copy dispatches.
        """
        # Sadly, the only way to do this is to change variables from the copy module
        # directly and by force.
        # But this only acts on MultiMeta and its subclasses, who are generally private,
        # so most of the time, the user might not even notice it.
        # It should then be safe enough to modify directly by force variables inside the
        # copy module. Note that no data is deleted here, we only add some.
        _D_COPY.print("Dispatching a new metatype...")
        copy.deepcopy.__globals__['_deepcopy_dispatch'][mcs] = mcs.deepcopy  # real location is copy._deepcopy_dispatch
        copy.copy.__globals__['_copy_dispatch'][mcs] = mcs.copy  # real location is copy._copy_dispatch

    def _register_typ_cache(cls, args, tp):
        cls._typecache[args] = tp

    @classmethod
    def copy(mcs, x):
        """
        Create and return a shallow copy of class x.
        Return None if x is not a type of the correct
        metaclass.
        """
        debugger.audit(f'{_LIB_NAME}.MultiMeta.copy', x)
        if not isinstance(x, mcs):
            return None
        return x.__copy__()

    @classmethod
    def deepcopy(mcs, x, memo={}):
        """
        Create and return a deep copy of class x.
        This copies one by one each attribute of x
        into a new equivalent type object.
        This means the source types' instances won't be
        considered instances of the new copy.
        Return None if x is not a type of the correct
        metaclass.
        """
        debugger.audit(f'{_LIB_NAME}.MultiMeta.deepcopy', x)
        if not isinstance(x, mcs):
            return None
        return x.__deepcopy__(memo)


# register MultiMeta into copy dispatches:
MultiMeta._register_copy_dispatches()


### -------- Helper Functions -------- ###

def _get_exporter(cls):
    mod = cls.__module__.split('.')
    exporter = _LIB_NAME
    if len(mod) > 2:
        sub = mod[1]
        exporter += '.' + sub
    return exporter


def _check_friends(friends):
    result = []
    for friend in friends:
        if not isinstance(friend, type):
            # user specified something that is not a type as a friend:
            raise err_depth(SyntaxError, 'Wrong syntax for class friendship (\'__friends__\'). See documentation for more info.', depth=2)
        if friend not in result:
            result.append(friend)
    return tuple(result)


def _typecheck_template_type(tp):
    if isinstance(tp, (type, type(Ellipsis))):
        return True
    if isinstance(tp, tuple):
        for t in tp:
            if not isinstance(t, (type, type(Ellipsis))):
                return False
        return True
    return False

def _template_type_repr(tp):
    if isinstance(tp, type):
        return tp.__name__
    if isinstance(tp, tuple):
        types = tuple((t.__name__ for t in tp))
        return ' | '.join(types)
    return None


def _build_template_list_repr(args):
    res = []
    for a in args:
        if isinstance(a, MultiMeta):
            res.append(a.__name__)
            continue
        if isinstance(a, str):
            res.append(repr(a))
            continue
        if hasattr(a, '__name__'):
            res.append(f"{type(a).__name__} {a.__name__}")
            continue
        res.append(str(a))

    return tuple(res)


def _func_without_code(func):
    if not isinstance(func, (Function, Method)):
        return func
    tp = Function if isinstance(func, Function) else Method
    return tp(_NOOP_CODE(), func.__globals__, func.__name__, func.__defaults__, func.__closure__)


def _typecheck_template(arg, tp):
    from ._parser import parse_args  # this is imported here to avoid circular import

    try:
        parse_args((arg,), tp)
    except AttributeError:
        return False
    return True

