import gc
import os.path
import types
from itertools import count
import sys

from . import type_flags

_error_handling = False


_tracelist = []


def _tracefunc(frame, event, args):
    if sys is None:
        return
    for trace in _tracelist:
        trace(frame, event, args)
    return _tracefunc


sys.settrace(_tracefunc)


def is_heaptype(cls):
    """
    Return whether t_instance is a Heap type.
    Heap types are allocated on the heap,
    as opposed to static types, which are
    allocated statically.
    More details here:
    https://docs.python.org/3/c-api/typeobj.html#static-types
    """
    return bool(type_flags.flags(cls) & type_flags.TPFLAGS_HEAPTYPE)


def settrace(fn):
    """
    Add a new tracing function.
    """
    _tracelist.append(fn)


def removetrace(fn):
    """
    Make the given function no longer a tracing function.
    """
    pos = None
    for i in range(len(_tracelist)):
        if id(_tracelist[i]) == id(fn):
            pos = i
            break
    if pos is not None:
        del _tracelist[pos]


def get_instances(cls):
    """
    Return a list of all the alive instances of class 't_instance'.
    """
    res = []
    # Heap type instances count as references to their type,
    # so gc.get_referrers() is a reliable and faster
    # alternative to gc.get_objects().
    # Static type instances don't count as a reference to
    # their type, so gc.get_referrers() is unreliable.
    if is_heaptype(cls):
        objs = gc.get_referrers(cls)  # yields a shorter list to iterate over: faster
    else:
        objs = gc.get_objects()  # can be very slow, so we prefer using get_referrers() if possible

    for ob in objs:
        if isinstance(ob, cls):
            res.append(ob)
    return res


def get_file_directory(file=None):
    """
    Return a file's directory.
    If file is unspecified, the current module is used
    instead. In that case, if the current module is not a file,
    FileNotFoundError is raised.
    """
    if file is None:
        frame = call_stack[1]
        file = frame.f_code.co_filename
    if file is None:
        raise FileNotFoundError("Current module is not a python file or package.")
    file = file.replace('/', os.path.sep)
    if file.startswith('<') and file.endswith('>'):
        raise FileNotFoundError("Current module is not a python file or package.")
    fn = file.split(os.path.sep)[-1]
    fd = file.removesuffix(fn)
    return fd


class Stack:
    """
    Class representing a basic stack.
    Can access a given element in the stack, given a function to do so.
    Can, if provided with a way to do so, determine the size of that stack.
    """
    def __init__(self, getitem, get_len=None):
        self._getitem = getitem
        self._get_len = get_len
        self._offset = 0
        self.__name__ = getitem.__name__
        self.__doc__ = getitem.__doc__ if hasattr(getitem, '__doc__') else None

    def _getlen_func(self, func):
        self._get_len = func
        return self

    def __getitem__(self, depth):
        return self._getitem(self, depth)

    def __len__(self):
        """
        Return, if possible, the size of the stack. Otherwise,
        return NotImplemented.
        """
        if not self._get_len:
            return NotImplemented
        return self._get_len(self)

    def __repr__(self):
        return f"<stack '{self.__name__}'>"

    def get(self):
        """
        Return the element at the top of the stack.
        """
        return self[0]


class WriteableStack(Stack):
    def __init__(self, getitem, get_len=None):
        super().__init__(getitem, get_len=get_len)
        self._pop = None
        self._push = None

    def _pop_func(self, fn):
        self._pop = fn

    def _push_func(self, fn):
        self._push = fn

    def pop(self):
        """
        Pop and return the item on the top of the stack.
        Return None if the stack is empty.
        """
        if not self._pop:
            return NotImplemented
        return self._pop(self)

    def push(self, obj):
        """
        Push obj on top of the stack.
        """
        if not self._push:
            return NotImplemented
        return self._push(self, obj)


@Stack
def call_stack(stack, depth):
    """
    The Python call stack.
    len(call_stack) calculates the depth of the stack,
    call_stack[i] yields the frame at depth i in the stack,
    call_stack.get() yields the frame at the top of the stack.
    """
    caller_size = len(stack)
    if depth < 0:
        depth = caller_size + depth
    try:
        return sys._getframe(depth + 2)
    except ValueError:
        from .errors import configure
        raise IndexError("Index out of range.") from configure(trace_depth=2)


# noinspection PyUnresolvedReferences
@call_stack._getlen_func
def call_stack(stack):
    """
    The Python call stack.
    len(call_stack) calculates the depth of the stack,
    call_stack[i] yields the frame at depth i in the stack,
    call_stack.get() yields the frame at the top of the stack.
    Always returns the call stack of the current thread.
    """
    size_hint = 1
    frame = None
    try:
        while True:
            frame = sys._getframe(size_hint)
            size_hint *= 2
    except ValueError:
        if frame:
            size_hint //= 2
        else:
            while not frame:
                size_hint = max(2, size_hint // 2)
                try:
                    frame = sys._getframe(size_hint)
                except ValueError:
                    continue

    for size in count(size_hint):
        frame = frame.f_back
        if not frame:
            return size - 1


def scope_at(module):
    """
    Add op into module's scope.
    The original reference to op is kept though.
    """
    if isinstance(module, str):
        module = sys.modules.get(module, None)
    if not isinstance(module, types.ModuleType):
        raise TypeError("'module' should be a module object or the name of an imported module.")

    def _inner(op):
        op.__module__ = module.__name__
        nodes = op.__qualname__.split('.')
        name = nodes[-1]
        nodes.pop(-1)

        scope = module
        for node in nodes:
            scope = getattr(scope, node)
        setattr(scope, name, op)
        return op
    return _inner

