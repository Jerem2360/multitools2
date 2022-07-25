import _thread
import random
import sys
import pickle
import types
import marshal
import binascii


from ._const import *


### -------- Basic classes to sort values on reference fixing when pickling and unpickling functions -------- ###

class _BltnInfo:
    """
    Basic class to indicate that a name required by a function
    resides inside the 'builtins' module.
    """
    def __init__(self, name='print'):
        self._name = name

    def __restore__(self):
        if self._name in globals():
            return globals()[self._name]
        import builtins
        return getattr(builtins, self._name)

    def __getstate__(self):
        return {'name': self._name}

    def __setstate__(self, state):
        self._name = state['name']


class _SysItemInfo:
    """
    Basic class to indicate that a name required by a function
    resides inside the 'sys' module.
    """
    def __init__(self, name='version_info'):
        self._name = name

    def __restore__(self):
        return getattr(sys, self._name)

    def __getstate__(self):
        return {'name': self._name}

    def __setstate__(self, state):
        self._name = state['name']


class _ModInfo:
    """
    Basic class to fix an import from a function.
    Also, this is handful because pickleable.
    **Non-static modules are not supported.**
    """
    def __init__(self, module=None):
        """
        Save a module's info.
        """
        if module is None:
            self._name = '<unknown>'
            return
        self._name = module.__name__
        if module.__package__ != '':
            if module.__package__.endswith(self._name):
                self._name = module.__package__
            else:
                self._name = module.__package__ + '.' + self._name

    @staticmethod
    def _import(name):
        """
        Internal helper that stores the imported module
        inside sys.modules if not already done.
        """
        # module has already been imported, return it:
        if name in sys.modules:
            return sys.modules[name]
        # module has not already been imported, so we import it into the new namespace:
        mod = __import__(name)
        sys.modules[name] = mod   # save it in sys.modules, so it doesn't get imported multiple times in the same namespace.
        return mod

    def __import__(self):
        """
        Restore the previously saved module by importing it.
        Returns the imported module.
        """
        # special case of '<unknown>':
        if self._name == '<unknown>':
            return None

        # the module has already been imported in the new namespace:
        if self._name in sys.modules:
            return sys.modules[self._name]

        # the module has a simple name with no dots, easy to import:
        if '.' not in self._name:
            return self._import(self._name)

        # the module has a dotted name, import each node, one after the other:
        self._import(self._name.split('.')[0])
        for i in range(len(self._name.split('.')) - 1):
            temp_name = self._name.split('.')[:i+1].join('.')
            self._import(temp_name)
        return self._import(self._name)

    def __getstate__(self):
        """
        Helper for pickle.
        """
        return {'name': self._name}

    def __setstate__(self, state):
        """
        Helper for pickle.
        """
        self._name = state['name']


class _PickledObjInfo:
    """
    Basic class that stores a value in pickled form, which can
    be restored later.
    """
    def __init__(self, obj=None):
        if obj is None:
            self._data = None
            return
        self._data = pickle.dumps(obj)

    def __restore__(self):
        if self._data is None:
            return None
        return pickle.loads(self._data)

    def __getstate__(self):
        return {'data': self._data}

    def __setstate__(self, state):
        self._data = state['data']

### -------- Function pickling-related functions -------- ###

def pickle_function(function, name: str):
    """
    Pickle a function as if it were any other type of standard
    python object. Pickle doesn't do this by default, and does
    name lookups only.
    """
    # special case where function is None:
    if function is None:
        return {f'{name}:name': None}

    # list references needed by the function inside a dict:
    needed_globals = {}
    for _name in function.__code__.co_names:
        # name was not found in the global scope of the function:
        if _name not in function.__globals__:
            needed_globals[_name] = None
            continue
        # name is a module that should be re-imported on unpickling:
        if isinstance(function.__globals__[_name], type(sys)):
            needed_globals[_name] = _ModInfo(function.__globals__[_name])
            continue
        # name resides in the sys module and should be re-imported on unpickling:
        if hasattr(sys, _name):
            needed_globals[_name] = _SysItemInfo(_name)
            continue
        # name is a builtin object and should be found in globals or re-imported from the builtins module:
        import builtins
        if hasattr(builtins, _name):
            needed_globals[_name] = _BltnInfo(_name)
            continue
        # name might be pickleable, we should try:
        try:
            needed_globals[_name] = _PickledObjInfo(function.__globals__[_name])
        except pickle.PicklingError:
            # it turns out that name was not pickleable, and well, where else could we find the object? No idea.
            # if the name turns out to be in globals() at function execution, the user is either lucky or smart.
            needed_globals[_name] = None

    # store every single attribute / sub-attribute of the function:
    result = {
        f'{name}:name': function.__name__,
        f'{name}:defaults': function.__defaults__,
        f'{name}:closure': function.__closure__,
        f'{name}:co_argcount': function.__code__.co_argcount,
        f'{name}:co_kwonlyargcount': function.__code__.co_kwonlyargcount,
        f'{name}:co_nlocals': function.__code__.co_nlocals,
        f'{name}:co_stacksize': function.__code__.co_stacksize,
        f'{name}:co_flags': function.__code__.co_flags,
        f'{name}:co_code': function.__code__.co_code,
        f'{name}:co_consts': function.__code__.co_consts,
        f'{name}:co_names': function.__code__.co_names,
        f'{name}:co_varnames': function.__code__.co_varnames,
        f'{name}:co_filename': function.__code__.co_filename,
        f'{name}:co_name': function.__code__.co_name,
        f'{name}:co_firstlineno': function.__code__.co_firstlineno,
        f'{name}:co_lnotab': function.__code__.co_lnotab,
        f'{name}:co_freevars': function.__code__.co_freevars,
        f'{name}:co_cellvars': function.__code__.co_cellvars,
        f'{name}:globals': needed_globals,
    }
    if sys.version_info >= (3, 8):
        result[f'{name}:co_posonlyargcount'] = function.__code__.co_posonlyargcount
    return result


def unpickle_function(state, name):
    """
    Unpickle a function as if it were of any type of standard
    python object. Pickle doesn't do this by default.
    """
    import sys

    # special case where function was None:
    if state[f'{name}:name'] is None:
        return None

    # restore the code of the function, and all of its attributes:
    code_args = [
        state[f'{name}:co_argcount'],
        state[f'{name}:co_kwonlyargcount'],
        state[f'{name}:co_nlocals'],
        state[f'{name}:co_stacksize'],
        state[f'{name}:co_flags'],
        state[f'{name}:co_code'],
        state[f'{name}:co_consts'],
        state[f'{name}:co_names'],
        state[f'{name}:co_varnames'],
        state[f'{name}:co_filename'],
        state[f'{name}:co_name'],
        state[f'{name}:co_firstlineno'],
        state[f'{name}:co_lnotab'],
        state[f'{name}:co_freevars'],
        state[f'{name}:co_cellvars'],
    ]
    if sys.version_info >= (3, 8):
        code_args.insert(1, state[f'{name}:co_posonlyargcount'])

    function_code = types.CodeType(*code_args)
    # restore the function itself, along with all of its attributes:
    function = types.FunctionType(
        function_code,
        globals(),
        state[f'{name}:name'],
        state[f'{name}:defaults'],
        state[f'{name}:closure'],
    )

    # fix any missing references needed by the function (if possible):
    glob = state[f'{name}:globals']
    for _name, value in glob.items():
        # the referenced object was a module, re-import it:
        if isinstance(value, _ModInfo):
            globals()[_name] = value.__import__()
            continue
        # the referenced object was a builtin object, re-import it:
        if isinstance(value, _BltnInfo):
            globals()[_name] = value.__restore__()
            continue
        # the referenced object resides inside the sys module, re-import it:
        if isinstance(value, _SysItemInfo):
            globals()[_name] = value.__restore__()
            continue
        # the referenced object was found to be pickleable, therefore unpickling it would restore its value:
        if isinstance(value, _PickledObjInfo):
            globals()[_name] = value.__restore__()
            continue
        # well, at this point, we found all values we could restore, but a lucky user might reference a name
        # already residing in globals()
        if value is None:
            pass

    return function


def pickle_function2(function):
    """
    Like pickle_function(), but nearly twice as efficient.
    bytes are nearly half of the length of that for pickle_function()
    """
    if function is None:
        return None

    # list references needed by the function inside a dict:
    needed_globals = {}
    for _name in function.__code__.co_names:
        # name was not found in the global scope of the function:
        if _name not in function.__globals__:
            needed_globals[_name] = None
            continue
        # name is a module that should be re-imported on unpickling:
        if isinstance(function.__globals__[_name], type(sys)):
            needed_globals[_name] = _ModInfo(function.__globals__[_name])
            continue
        # name resides in the sys module and should be re-imported on unpickling:
        if hasattr(sys, _name):
            needed_globals[_name] = _SysItemInfo(_name)
            continue
        # name is a builtin object and should be found in globals or re-imported from the builtins module:
        import builtins
        if hasattr(builtins, _name):
            needed_globals[_name] = _BltnInfo(_name)
            continue
        # name might be pickleable, we should try:
        try:
            needed_globals[_name] = _PickledObjInfo(function.__globals__[_name])
        except pickle.PicklingError:
            # it turns out that name was not pickleable, and well, where else could we find the object? No idea.
            # if the name turns out to be in globals() at function execution, the user is either lucky or smart.
            needed_globals[_name] = None

    # store every single attribute of the function:
    result = {
        'name': function.__name__,
        'defaults': function.__defaults__,
        'closure': function.__closure__,
        'code': marshal.dumps(function.__code__),  # marshalling the function's code optimizes the size of the data.
        'globals': needed_globals,
        '__is_function': True
    }
    if sys.version_info >= (3, 8):
        result['co_posonlyargcount'] = function.__code__.co_posonlyargcount

    return pickle.dumps(result)


def unpickle_function2(state):
    """
    Like unpickle_function(), but nearly twice as efficient.
    bytes are nearly half of the length of that for unpickle_function()
    """
    data = pickle.loads(state)
    code = marshal.loads(data['code'])

    function = types.FunctionType(
        code,
        globals(),
        data['name'],
        data['defaults'],
        data['closure'],
    )

    glob = data['globals']
    for _name, value in glob.items():
        # the referenced object was a module, re-import it:
        if isinstance(value, _ModInfo):
            globals()[_name] = value.__import__()
            continue
        # the referenced object was a builtin object, re-import it:
        if isinstance(value, _BltnInfo):
            globals()[_name] = value.__restore__()
            continue
        # the referenced object resides inside the sys module, re-import it:
        if isinstance(value, _SysItemInfo):
            globals()[_name] = value.__restore__()
            continue
        # the referenced object was found to be pickleable, therefore unpickling it would restore its value:
        if isinstance(value, _PickledObjInfo):
            globals()[_name] = value.__restore__()
            continue
        # well, at this point, we found all values we could restore, but a lucky user might reference a name
        # already residing in globals()
        if value is None:
            pass

    return function

### -------- Other miscellaneous functions -------- ###


def metaclassof(op) -> type[type]:
    """
    Return the metaclass of op.
    """
    if isinstance(op, type):
        return op.__class__
    return op.__class__.__class__


def print_stacktrace(exception):
    """
    Print a stacktrace for the provided exception object in the current frame.
    """
    try:
        raise exception
    except:
        sys.excepthook(*sys.exc_info())


def random_hex(length):
    """
    Create and return random bytes of given length.
    """
    binascii.hexlify(random.Random().randbytes(length)).decode('ascii')


def nameof(identifier):
    """
    Create and return a name from a given identifier.
    """
    name = SHM_NAME_PREFIX + hex(identifier).removeprefix('0x')
    if len(name) > SHM_SAFE_NAME_LENGTH:
        raise OverflowError("Identifier too big.")
    return name


def match_length(data, length, trail=b'\x00'):
    if len(data) > length:
        return data[:length]
    if len(data) < length:
        diff = length - len(data)
        for i in range(diff):
            data += trail
        return data
    return data


class Synchronizer:
    """
    A type that attaches to a given instance that supports the Synchronizing protocol.
    It can lock, unlock and wait for the given instance, allowing to synchronize it
    amongst multiple threads.

    By default, this protocol supports threading.Lock instances.

    To implement this protocol, it is recommended that the 'locked or not' state
    is stored somewhere inside the instance. It is also required to implement the
    __lock__() and __unlock__() methods as well as the readonly __locked__ property.
    An optional __wait__() method can also be implemented.
    """

    def __new__(cls, *args, **kwargs):
        """
        Create and return a new Synchronizer object.
        """
        self = super().__new__(cls)
        self._inst = _thread.allocate_lock()  # default value
        return self

    def __init__(self, instance):
        """
        Initialize a Synchronizer object, given an instance to attach to.
        """
        if (hasattr(instance, '__lock__') and hasattr(instance, '__unlock__') and hasattr(instance, '__locked__')) or \
                isinstance(instance, _thread.LockType):
            self._inst = instance
            return
        raise TypeError("The type of the given instance does not support the Synchronization protocol.")

    def _get_locked(self):
        if isinstance(self._inst, _thread.LockType):
            return self._inst.locked()
        return self._inst.__locked__

    def lock(self, *args, **kwargs):
        """
        Lock the underlying instance.
        """
        if isinstance(self._inst, _thread.LockType):
            return self._inst.acquire(*args, **kwargs)
        return self._inst.__lock__(*args, **kwargs)

    def unlock(self):
        """
        Unlock the underlying instance.
        """
        if isinstance(self._inst, _thread.LockType):
            return self._inst.release()
        return self._inst.__unlock__()

    def wait(self):
        """
        Wait until the instance is unlocked by another thread.
        """
        if isinstance(self._inst, _thread.LockType):
            self._inst.acquire()
            return self._inst.release()
        if hasattr(self._inst, '__wait__'):
            return self._inst.__wait__()
        while True:
            if not self._get_locked():
                break

    def __enter__(self):
        """
        Implement with self
        """
        if not isinstance(self._inst, _thread.LockType):
            self.wait()
        self.lock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Implement with self
        """
        self.unlock()

    def __reduce__(self):
        """
        Helper for pickle.
        """
        return (
            self.__class__,
            (self._inst,)
        )

    locked = property(lambda self: self._get_locked())

