import pickle
import sys
import traceback
from multiprocessing import shared_memory

from ._const import *
from ._typing import *
from ._errors import *
from ._helpers import *
from ._builtindefs import *

SIZE_EMPTY = len(pickle.dumps({}))
EMPTY = pickle.dumps({})

LOCKED_TRUE = (1).to_bytes(2, 'big', signed=False)
LOCKED_FALSE = (0).to_bytes(2, 'big', signed=False)

DATA_IS_FUNCTION = b'\xFF'


def _remove_trailing_nul_chars(string):
    while True:
        if not string.endswith('\x00'):
            break
        string = string.removesuffix('\x00')
    return string


def _add_n_trailing_nul_bytes(data, n):
    for _ in range(n):
        data += b'\x00'
    return data


class _SharedMemory(shared_memory.SharedMemory):
    def __del__(self):
        if not MS_WINDOWS:
            self.close()


class SharedDict:
    def __init__(self, name=None, create=False, serializer=None):
        type_check((name, create), (str, None), bool)

        if not create and name is None:
            raise TypeError(TYPE_ERR_STR.format('str', type(name).__name__))

        if serializer is None:
            serializer = PickleSerializer

        self._serializer = serializer

        if create:
            self._data_memory = _SharedMemory(create=True, size=SIZE_EMPTY)
            self._data_memory.buf[:] = EMPTY

            data_name = self._data_memory.name
            data_name_b = bytes(data_name, encoding=DEFAULT_ENCODING)

            header_contents = SIZE_EMPTY.to_bytes(8, 'big', signed=False) + data_name_b
            header_size = len(header_contents)

            self._pre_header = _SharedMemory(name=name, create=True, size=6)
            # format: 2 first bytes = locked [UBOOL]; 4 other bytes = header_size [UINT]
            pre_header_contents = LOCKED_TRUE + header_size.to_bytes(4, 'big', signed=False)
            # above, locked is set to TRUE until the shared memory has completely finished initializing

            self._pre_header.buf[:] = pre_header_contents

            self._header = _SharedMemory(name=self._pre_header.name + ':head', create=True, size=header_size)
            self._header.buf[:] = header_contents

            self._pre_header.buf[:2] = LOCKED_FALSE

        else:
            self._pre_header = _SharedMemory(name=name, create=False, size=6)
            # self._wait_until_unlock_no_check()
            self._pre_header.buf[:2] = LOCKED_TRUE
            try:
                self._header = self._get_header_no_check()
                self._data_memory = self._get_data_memory_no_check()
            finally:
                self._pre_header.buf[:2] = LOCKED_FALSE

        self._SYNC = _SharedMemorySynchronizer(self, limit=100)
        self._closed = False
        print('starting')

    def _check_open(self):
        # print(self._pre_header.buf, self._header.buf, self._data_memory.buf)
        if self._pre_header.buf is None:
            self._closed = True
        if self._closed:
            raise MemoryError('IO operation on closed memory block.')

    def _wait_until_unlock_no_check(self, limit=-1):
        # print('start')
        counter = 0
        while True:
            # print(bytes(self._pre_header.buf[:2]), LOCKED_FALSE, LOCKED_TRUE)
            if bytes(self._pre_header.buf[:2]) == LOCKED_FALSE:
                break
            if (limit > 0) and (counter >= limit):
                break
            counter += 1

    def _wait_until_unlock(self, limit=-1):
        self._check_open()
        self._wait_until_unlock_no_check(limit)

    def _get_header(self):
        self._check_open()
        return self._get_header_no_check()

    def _get_header_no_check(self):
        size = int.from_bytes(self._pre_header.buf[2:], 'big', signed=False)
        name = self._pre_header.name + ':head'
        return _SharedMemory(name=name, create=False, size=size)

    def _get_data_memory(self):
        self._check_open()
        return self._get_data_memory_no_check()

    def _get_data_memory_no_check(self):
        size = int.from_bytes(self._header.buf[:8], 'big', signed=False)
        name = str(bytes(self._header.buf[8:]), encoding=DEFAULT_ENCODING)
        return _SharedMemory(name=_remove_trailing_nul_chars(name), size=size, create=False)

    def _update(self):
        self._check_open()
        new_header = self._get_header()
        if new_header.name != self._header.name:
            self._header.close()
        self._header = new_header

        new_data_memory = self._get_data_memory()
        if new_data_memory.name != self._data_memory.name:
            self._data_memory.close()
        self._data_memory = new_data_memory

    def _lock(self):
        self._check_open()
        self._pre_header.buf[:2] = LOCKED_TRUE

    def _unlock(self):
        self._check_open()
        self._pre_header.buf[:2] = LOCKED_FALSE

    def _resize(self, size):
        self._check_open()
        self._update()
        if size != self._data_memory.size:
            data = self._data_memory.buf[:]
            if size > self._data_memory.size:
                diff = size - self._data_memory.size
                data = _add_n_trailing_nul_bytes(data, diff)
            else:
                data = data[:size]

            self._data_memory = _SharedMemory(create=True, size=size)
            self._data_memory.buf[:] = data

            data_name_b = bytes(self._data_memory.name, encoding=DEFAULT_ENCODING)
            data_size_b = self._data_memory.size.to_bytes(8, 'big', signed=False)

            header_contents = data_size_b + data_name_b

            self._header.close()
            self._header.unlink()

            self._header = _SharedMemory(name=self._pre_header.name + ':head', create=True, size=len(header_contents))
            self._header.buf[:] = header_contents

            self._pre_header.buf[2:] = self._header.size.to_bytes(4, 'big', signed=False)

    def _set_data(self, new_data):
        self._check_open()
        data_b = self._serializer.serialize(new_data)
        self._resize(len(data_b))  # already calls self._update()
        self._data_memory.buf[:] = data_b

    def _get_data(self):
        self._check_open()
        self._update()
        data_b = bytes(self._data_memory.buf[:])
        return self._serializer.deserialize(data_b)

    def clear(self):
        with self._SYNC:
            self._resize(SIZE_EMPTY)
            self._data_memory.buf[:] = EMPTY

    def copy(self):
        with self._SYNC:
            return self._get_data()

    def popitem(self):
        with self._SYNC:
            data = self._get_data()
            res = data.popitem()
            self._set_data(data)
        return res

    def set_default(self, key, default):
        with self._SYNC:
            data = self._get_data()
            res = data.set_default(key, default)
            self._set_data(data)
        return res

    def update(self, mapping, **kwargs):
        with self._SYNC:
            data = self._get_data()
            res = data.update(mapping, **kwargs)
            self._set_data(data)
        return res

    def keys(self):
        with self._SYNC:
            return self._get_data().keys()

    def values(self):
        with self._SYNC:
            return self._get_data().values()

    def items(self):
        with self._SYNC:
            return self._get_data().items()

    def free(self):
        self._SYNC.wait()
        self._data_memory.unlink()
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
        with self._SYNC:
            self._set_data(new_data)
        return self

    @classmethod
    def from_dict(cls, source, name=None):
        type_check((source, name), dict, (str, None))
        self = cls(name=name, create=True)
        self._lock()
        self._set_data(source)
        self._unlock()
        return self

    @classmethod
    def load(cls, name):
        type_check((name,), str)
        return cls(name=name, create=False)

    @classmethod
    def create(cls, name=None):
        type_check((name,), (str, None))
        return cls(name=name, create=True)

    def __getitem__(self, item):
        with self._SYNC:
            return self._get_data()[item]

    def __setitem__(self, key, value):
        with self._SYNC:
            data = self._get_data()
            data[key] = value
            self._set_data(data)

    def __delitem__(self, key):
        with self._SYNC:
            data = self._get_data()
            del data[key]
            self._set_data(data)

    def __iter__(self):
        with self._SYNC:
            return iter(self._get_data())

    def __len__(self):
        with self._SYNC:
            return len(self._get_data())

    def __reversed__(self):
        with self._SYNC:
            return reversed(self._get_data())

    def __str__(self):
        with self._SYNC:
            return str(self._get_data())

    def __repr__(self):
        return f"{GLOBAL_NAME}.SharedDict({str(self)})"

    def __class_getitem__(cls, item):
        return dict[item]

    def __or__(self, other):
        data = other
        if isinstance(other, SharedDict):
            with other._SYNC:
                data = other._get_data()

        with self._SYNC:
            my_data = self._get_data()

        return my_data | data

    def __ror__(self, other):
        data = other
        if isinstance(other, SharedDict):
            with other._SYNC:
                data = other._get_data()

        with self._SYNC:
            my_data = self._get_data()

        return data | my_data

    def __ior__(self, other):
        return self.__or__(other)

    def __getstate__(self):
        self._update()
        return bytes(self._pre_header.name, encoding=DEFAULT_ENCODING) + b';' + bytes(self._data_memory[:])

    def __setstate__(self, state):
        name_b, data_b = state.split(b';', 1)
        existed = False
        name = str(name_b, encoding=DEFAULT_ENCODING)

        try:
            self._pre_header = _SharedMemory(name=name, create=True, size=6)
        except FileExistsError:
            existed = True
            self._pre_header = _SharedMemory(name=name, create=False, size=6)

        if existed:
            self._header = self._get_header()
            self._data_memory = self._get_data_memory()

        else:
            self._data_memory = None
            self._header = None
            self._pre_header = None

    def __del__(self):
        try:
            self._unlock()
        except:
            pass

    @property
    def contents(self):
        self._check_open()
        with self._SYNC:
            return self._get_data()

    name = property(lambda self: self._pre_header.name)


class _SharedMemorySynchronizer:
    def __init__(self, instance, limit=-1):
        self._inst = instance
        self._limit = limit

    def wait(self):
        # noinspection PyProtectedMember
        self._inst._wait_until_unlock(self._limit)

    def lock(self):
        # noinspection PyProtectedMember
        self._inst._lock()

    def unlock(self):
        # noinspection PyProtectedMember
        self._inst._unlock()

    def __enter__(self):
        # print('enter sync')
        self.wait()
        self.lock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # print('exit_sync')
        self.unlock()


class Serializer:
    @staticmethod
    def serialize(obj): ...
    @staticmethod
    def deserialize(data): ...


class PickleSerializer(Serializer):
    @staticmethod
    def serialize(obj):
        if isinstance(obj, (Function, Method)):
            pickled = pickle_function2(obj)
            if pickled is None:
                return pickle.dumps(None)
            return DATA_IS_FUNCTION + pickled
        try:
            return pickle.dumps(obj)
        except pickle.PicklingError:
            raise change_error(ValueError('PickleSerializer only supports pickleable objects.'))

    @staticmethod
    def deserialize(data):
        if data.startswith(DATA_IS_FUNCTION):
            return unpickle_function2(data.removeprefix(DATA_IS_FUNCTION))
        return pickle.loads(data)

