import pickle
from multiprocessing import shared_memory
import sys

from .._local import *
from .._typing import *
from .._const import *
from .._builtindefs import *
from .._helpers import *

SYNC = Synchronizer()
SIZE_EMPTY = len(pickle.dumps({}))
SIZE_EMPTY_B = SIZE_EMPTY.to_bytes(8, 'big', signed=False)
EMPTY = pickle.dumps({})


def _pickle_obj(obj):
    if isinstance(obj, Function):
        return pickle_function2(obj)
    return pickle.dumps(obj)


def _unpickle_obj(pickled_data):
    data = pickle.loads(pickled_data)
    if isinstance(data, dict) and \
            '__is_function' in data and data['__is_function']:
        return unpickle_function2(pickled_data)
    return pickle.loads(pickled_data)


class _SharedMemory(shared_memory.SharedMemory):
    def __del__(self):  # on Windows, the shared memory must not close itself upon deletion.
        if not MS_WINDOWS:
            self.close()


def _remove_trailing_null_chars(string):
    while True:
        if not string.endswith('\x00'):
            break
        string = string.removesuffix('\x00')
    return string


def _add_n_trailing_null_bytes(data, n):
    for i in range(n):
        data += b'\x00'
    return data


class SharedDict:
    pickle_raise = False
    """
    Used when the object gets unpickled and finds out that its memory no longer exists.
    If True, a Reference error will be raised.
    If False, a new shared memory will be created with the correct name and the old data will be restored.
    May be changed throughout runtime.
    """

    def __init__(self, name=None, create=False):

        type_check((create, name), bool, (str, None))

        if not create and name is None:
            raise TypeError(TYPE_ERR_STR.format('str', type(name).__name__))

        if create:
            self._data_memory = _SharedMemory(create=True, size=SIZE_EMPTY)
            with SYNC:
                self._data_memory.buf[:] = EMPTY

            data_name = self._data_memory.name
            data_name_b = bytes(data_name, encoding=DEFAULT_ENCODING)

            header_contents = SIZE_EMPTY_B + data_name_b
            header_size = len(header_contents)

            self._pre_header = _SharedMemory(name=name, create=True, size=4)
            with SYNC:
                self._pre_header.buf[:] = header_size.to_bytes(4, 'big', signed=False)

            self._header = _SharedMemory(name=self._pre_header.name + ':head', create=True, size=header_size)
            with SYNC:
                self._header.buf[:] = header_contents


        else:
            self._pre_header = _SharedMemory(name=name, create=False, size=4)
            self._header = self._get_header()
            self._data_memory = self._get_data_buf()

    def _get_header(self):
        size = int.from_bytes(self._pre_header.buf[:], 'big', signed=False)
        name = self._pre_header.name + ':head'
        return _SharedMemory(name=name, create=False, size=size)

    def _get_data_buf(self):
        size = int.from_bytes(self._header.buf[:8], 'big', signed=False)
        name = str(bytes(self._header.buf[8:]), encoding=DEFAULT_ENCODING)
        return _SharedMemory(name=_remove_trailing_null_chars(name), size=size, create=False)

    def _update(self):
        new_header = self._get_header()
        if new_header.name != self._header.name:
            self._header.close()
        self._header = new_header

        new_data_memory = self._get_data_buf()
        if new_data_memory.name != self._data_memory.name:
            self._data_memory.close()
        self._data_memory = new_data_memory

    def _resize(self, size):
        self._update()
        if size != self._data_memory.size:
            data = self._data_memory.buf[:]
            if size > self._data_memory.size:
                diff = size - self._data_memory.size
                data = _add_n_trailing_null_bytes(data, diff)
            else:
                data = data[:size]

            self._data_memory = _SharedMemory(create=True, size=size)
            self._data_memory.buf[:] = data

            data_name_b = bytes(self._data_memory.name, encoding=DEFAULT_ENCODING)
            data_size_b = self._data_memory.size.to_bytes(8, 'big', signed=False)

            header_contents = data_size_b + data_name_b

            self._header.close()
            self._header = _SharedMemory(name=self._pre_header.name + ':head', create=True, size=len(header_contents))
            self._header.buf[:] = header_contents

            self._pre_header.buf[:] = self._header.size.to_bytes(4, 'big', signed=False)

    def _set_data(self, new_data):
        try:
            data_b = _pickle_obj(new_data)
        except pickle.PicklingError:
            raise ValueError("Shared dictionaries can only store pickleable objects.") from None

        self._resize(len(data_b))  # already calls self._update()
        self._data_memory.buf[:] = data_b

    def _get_data(self):
        self._update()
        data_b = bytes(self._data_memory.buf[:])
        return _unpickle_obj(data_b)

    def clear(self):
        with SYNC:
            self._resize(len(EMPTY))  # already calls self._update()
            self._data_memory.buf[:] = EMPTY

    def copy(self):
        with SYNC:
            return self._get_data().copy()

    def popitem(self):
        with SYNC:
            data = self._get_data()
            res = data.popitem()
            self._set_data(data)
        return res

    def set_default(self, key, default):
        with SYNC:
            data = self._get_data()
            res = data.set_default(key, default)
            self._set_data(data)
        return res

    def update(self, mapping, **kwargs):
        with SYNC:
            data = self._get_data()
            res = data.update(mapping, **kwargs)
            self._set_data(data)
        return res

    def keys(self):
        with SYNC:
            return self._get_data().keys()

    def values(self):
        with SYNC:
            return self._get_data().values()

    def items(self):
        with SYNC:
            return self._get_data().items()

    def free(self):
        """
        Free the memory associated with this instance.
        When the dictionary is no longer needed, this method should be called, otherwise there could be
        memory leaks. However, only one call amongst all processes is required to free the memory.
        For auto-freeing shared memory, see the multiprocessing.sheared_memory.
        """
        self._data_memory.unlink()  # does nothing on Windows
        self._header.unlink()
        self._pre_header.unlink()

        try:
            self._data_memory.close()
            self._header.close()
            self._pre_header.close()
        except:
            pass

    @classmethod
    def fromkeys(cls, *args, **kwargs):
        new_data = dict.fromkeys(*args, **kwargs)
        self = cls(create=True)
        with SYNC:
            self._set_data(new_data)
        return self

    @classmethod
    def from_dict(cls, source, name=None):
        """
        Create and return a new shared dictionary, given source.
        """
        type_check((source, name), dict, (str, None))
        self = cls(name=name, create=True)
        with SYNC:
            self._set_data(source)
        return self

    @classmethod
    def load(cls, name):
        """
        Load and return an existing shared dictionary.
        """
        type_check((name,), str)
        return cls(name=name, create=False)

    @classmethod
    def create(cls, name=None):
        """
        Create and return a new empty shared dictionary.
        """
        type_check((name,), (str, None))
        return cls(name=name, create=True)

    def __getitem__(self, item):
        """
        Implement self[item]
        """
        with SYNC:
            return self._get_data()[item]

    def __setitem__(self, key, value):
        """
        Implement self[key] = value
        """
        with SYNC:
            data = self._get_data()
            data[key] = value
            self._set_data(data)

    def __delitem__(self, key):
        """
        Implement del self[key]
        """
        with SYNC:
            data = self._get_data()
            del data[key]
            self._set_data(data)

    def __iter__(self):
        """
        Implement iter(self)
        """
        with SYNC:
            return iter(self._get_data())

    def __len__(self):
        """
        Implement len(self)
        """
        with SYNC:
            return len(self._get_data())

    def __reversed__(self):
        """
        Implement reversed(self)
        """
        with SYNC:
            return reversed(self._get_data())

    def __str__(self):
        """
        Implement str(self)
        """
        with SYNC:
            return str(self._get_data())

    def __repr__(self):
        """
        Implement repr(self)
        """
        return f"{GLOBAL_NAME}._shared_memory.SharedDict({str(self)})"

    def __class_getitem__(cls, item):
        """
        Implement cls[item]
        """
        return dict[item]

    def __or__(self, other):
        """
        Implement self | other
        """
        data = other
        with SYNC:
            if isinstance(other, SharedDict):
                data = other._get_data()
            my_data = self._get_data()
        return my_data | data

    def __ror__(self, other):
        """
        Implement other | self
        """
        data = other
        with SYNC:
            if isinstance(other, SharedDict):
                data = other._get_data()
            my_data = self._get_data()
        return data | my_data

    def __ior__(self, other):
        """
        Implement self |= other
        """
        return self.__or__(other)

    def __getstate__(self):
        """
        Helper for pickle.
        """
        # state is directly bytes to speed up process.
        self._update()
        # state format is b'<name>;<data>' :
        return bytes(self._pre_header.name, encoding=DEFAULT_ENCODING) + b';' + bytes(self._data_memory[:])

    def __setstate__(self, state):
        """
        Helper for pickle.
        """
        # here, we don't just call the constructor because we don't know in advance
        # if the shared memory still exists.
        name_b, data_b = state.split(b';', 1)
        existed = False
        name = str(name_b, encoding=DEFAULT_ENCODING)
        # if the shared memory still exists, we bind to it, otherwise re-create it and restore data.
        try:
            self._pre_header = _SharedMemory(name=name, create=True, size=4)
        except FileExistsError:
            existed = True
            self._pre_header = _SharedMemory(name=name, create=False, size=4)

        if existed:
            self._header = self._get_header()
            self._data_memory = self._get_data_buf()

        else:
            if self.pickle_raise:
                raise ReferenceError(f"Shared memory '{name}' does not exist.")
            self._data_memory = _SharedMemory(create=True, size=SIZE_EMPTY)
            with SYNC:
                self._data_memory.buf[:] = data_b

            name_b = bytes(self._data_memory.name, encoding=DEFAULT_ENCODING)
            size_b = self._data_memory.size.to_bytes(8, 'big', signed=False)

            header_contents = size_b + name_b

            self._header = _SharedMemory(name=name, create=True, size=len(header_contents))
            with SYNC:
                self._header.buf[:] = header_contents
                self._pre_header.buf[:] = self._header.size.to_bytes(4, 'big', signed=False)

    @property
    def contents(self):
        """
        The contents of the shared dictionary, in form
        of a standard dictionary.
        """
        with SYNC:
            return self._get_data()

    name = property(lambda self: self._pre_header.name)
    """The name of the shared dictionary. Used to reference it from other instances and processes."""


_SHARED_NP_ALLOWED = (
    '_dict2987',
    'namespace_mapping',
    'free_namespace',
    'namespace_name'
)


class SharedNamespace:
    def __init__(self, name=None, create=True):
        self._dict2987 = SharedDict(name=name, create=create)
        self.__name__ = self._dict2987.name

    def __getattr__(self, item):
        if item == '__dict__':
            return self.mapping
        if (item in _SHARED_NP_ALLOWED) or (item.startswith('__') and item.endswith('__')):
            return super().__getattribute__(item)
        return self._dict2987[item]

    def __setattr__(self, key, value):
        if (key in _SHARED_NP_ALLOWED) or (key.startswith('__') and key.endswith('__')):
            return super().__setattr__(key, value)
        self._dict2987[key] = value

    def __delattr__(self, key):
        if key == '__dict__':
            raise AttributeError(f"Attribute '{key}' cannot be deleted.")
        if (key in _SHARED_NP_ALLOWED) or (key.startswith('__') and key.endswith('__')):
            return super().__delattr__(key)
        del self._dict2987[key]

    def __dir__(self):
        _names = list([key for key in self.namespace_mapping])
        _names.extend(_SHARED_NP_ALLOWED)
        for name in super().__dir__():
            if name.startswith('__') and name.endswith('__'):
                _names.append(name)
        return _names

    def __getstate__(self):
        return pickle.dumps(self._dict2987)

    def __setstate__(self, state):
        self._dict2987 = pickle.loads(state)
        self.__name__ = self._dict2987.name

    def __str__(self):
        return str(self._dict2987)

    def __repr__(self):
        return f"<shared namespace '{self.namespace_name}'>"

    def free_namespace(self):
        """
        Free the namespace.
        """
        self._dict2987.free()

    @classmethod
    def create(cls, **initial_values):
        self = cls.__new__(cls)
        self._dict2987 = SharedDict.from_dict(initial_values, name=None)
        return self

    @classmethod
    def load(cls, name):
        type_check((name,), str)
        self = cls.__new__(cls)
        self._dict2987 = SharedDict(name=name, create=False)
        return self

    @property
    def namespace_mapping(self):
        """
        The mapping associated with the namespace.
        """
        return self._dict2987.contents

    namespace_name = property(lambda self: self._dict2987.name)
    """The name of the namespace. Used to reference it from other processes."""
