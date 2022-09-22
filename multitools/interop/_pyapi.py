from ._structure import Struct as _Struct
from ._int_types import SSize_t as _Py_ssize_t, ULong, UInt
from ._pointer import Pointer
from ._chars import Char


"""
To signal pointer types that they point to a special type,
a _special marker is used. In this case, special pointer types
can be casted to a regular python objects.

values it can take:
    object => PyObject*, gets casted to '<class 'object'>' instances
    type => PyTypeObject*, gets casted to '<class 'type'>' instances
    str => [const] wchar_t*, gets casted to a python string.
    bytes => [const] char*, gets casted to a python bytes object.    
    None | ellipsis => gets casted to a python int i.e. the address pointed to
"""


class PyObject(_Struct):
    _special = object  # marker for PyObject* and friends

    ob_refcnt: _Py_ssize_t
    ob_type: Pointer  # real type is "Pointer[PyTypeObject]"


class PyVarObject(_Struct):
    ob_base: PyObject
    ob_size: _Py_ssize_t


class PyTypeObject(_Struct):
    _special = type  # marker for PyTypeObject* and friends

    ob_base: PyVarObject
    tp_name: Pointer[Char]
    tp_basicsize: _Py_ssize_t
    tp_itemsize: _Py_ssize_t
    tp_vectorcall_offset: _Py_ssize_t
    tp_getattr: Pointer  # real type is Pointer[CFunction]
    tp_setattr: Pointer  # real type is Pointer[CFunction]
    tp_as_async: Pointer  # real type is Pointer[PyAsyncMethods]
    tp_repr: Pointer  # real type is Pointer[CFunction]
    tp_as_number: Pointer  # real type is Pointer[PyNumberMethods]
    tp_as_sequence: Pointer  # real type is Pointer[PySequenceMethods]
    tp_as_mapping: Pointer  # real type is Pointer[PyMappingMethods]
    tp_hash: Pointer  # real type is Pointer[CFunction]
    tp_call: Pointer  # real type is Pointer[CFunction]
    tp_str: Pointer  # real type is Pointer[CFunction]
    tp_getattro: Pointer  # real type is Pointer[CFunction]
    tp_setattro: Pointer  # real type is Pointer[CFunction]
    tp_as_buffer: Pointer  # real type is Pointer[PyBufferProcs]
    tp_flags: ULong
    tp_doc: Pointer[Char]
    tp_traverse: Pointer  # real type is Pointer[CFunction]
    tp_clear: Pointer  # real type is Pointer[CFunction]
    tp_richcompare: Pointer  # real type is Pointer[CFunction]
    tp_weaklistoffset: _Py_ssize_t
    tp_iter: Pointer  # real type is Pointer[CFunction]
    tp_iternext: Pointer  # real type is Pointer[CFunction]
    tp_methods: Pointer  # real type is Pointer[PyMethodDef]
    tp_members: Pointer  # real type is Pointer[PyMemberDef]
    tp_getset: Pointer  # real type is Pointer[PyGetSetDef]
    tp_base: Pointer  # real type is Pointer[PyTypeObject]
    tp_dict: Pointer[PyObject]
    tp_descr_get: Pointer  # real type is Pointer[CFunction]
    tp_descr_set: Pointer  # real type is Pointer[CFunction]
    tp_dictoffset: _Py_ssize_t
    tp_init: Pointer  # real type is Pointer[CFunction]
    tp_alloc: Pointer  # real type is Pointer[CFunction]
    tp_new: Pointer  # real type is Pointer[CFunction]
    tp_free: Pointer  # real type is Pointer[CFunction]
    tp_is_gc: Pointer  # real type is Pointer[CFunction]
    tp_bases: Pointer[PyObject]
    tp_mro: Pointer[PyObject]
    tp_cache: Pointer[PyObject]
    tp_subclasses: Pointer[PyObject]
    tp_weaklist: Pointer[PyObject]
    tp_del: Pointer  # real type is Pointer[CFunction]
    tp_version_tag: UInt
    tp_finalize: Pointer  # real type is Pointer[CFunction]
    tp_vectorcall: Pointer  # real type is Pointer[CFunction]

