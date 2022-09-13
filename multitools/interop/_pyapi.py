from ._structure import Struct as _Struct
from ._int_types import SSize_t as _Py_ssize_t, ULongLong as _ptrlike


"""
To signal pointer types that they point to a special type,
a _special marker is used. In this case, special pointer types
can be casted to a regular python objects.

values it can take:
    object => PyObject*, gets casted to '<class 'object'>' instances
    type => PyTypeObject*, gets casted to '<class 'type'>' instances
    str => [const] wchar_t*, gets casted to a python string.
    bytes => [const] char*, gets casted to a python bytes object.    
    None | ellipsis => gets casted to a python int.
"""


class PyObject(_Struct):
    _special = object  # marker for PyObject* and friends

    ob_refcnt: _Py_ssize_t
    ob_type: _ptrlike  # real type is "Pointer[PyTypeObject]"


class PyTypeObject(_Struct):
    _special = type  # marker for PyTypeObject* and friends

    tp_name: _ptrlike  # real type is "Pointer[Char]"
    tp_basicsize: _Py_ssize_t
    tp_itemsize: _Py_ssize_t

