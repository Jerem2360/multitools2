import builtins
import ctypes
import _ctypes
import os
import _winapi
import sys
import cffi
import struct

from multitools2._internal import dllimport

class C:
    def __init__(self, dtype, data):
        self._as_parameter_ = dtype, data, None



hdll = dllimport.dlopen("C:/Windows/system32/kernel32.dll", 0)

hfunction = dllimport.dlsym(hdll, "GetProcAddress")


c_hdll = ctypes.cast(hdll, ctypes.c_void_p)
c_funcname = ctypes.create_string_buffer(b"GetProcAddress")

print(c_funcname, c_funcname.raw)

res = _ctypes.call_function(hfunction, (C('P', hdll), b"GetProcAddress\x00"))
res = res.to_bytes(8, sys.byteorder)
res = int.from_bytes(res, sys.byteorder, signed=False)
print(res, hfunction)
print(res, ctypes.FormatError())


"""import struct
import signal
import faulthandler
import gc
import sys

theirexec = builtins.exec

def myexec(*args, **kwargs):
    print("exec", args, kwargs)
    return theirexec(*args, **kwargs)


builtins.exec = myexec


from multitools2.interop import *

from multitools2.interop import better_pointers


class PyObject(Structure):
    ob_type: Pointer['PyTypeObject']
    ob_refcnt: Py_ssize_t


class PyVarObject(Structure):
    ob_base: PyObject
    ob_size: Py_ssize_t


class PyTypeObject(Structure):
    ob_base: PyVarObject

    tp_name: Pointer[Char]
    tp_basicsize: Py_ssize_t
    tp_itemsize: Py_ssize_t
    tp_vectorcall_offset: Py_ssize_t
    tp_getattr: Pointer[void]
    tp_setattr: Pointer[void]
    tp_as_async: Pointer[void]
    tp_repr: Pointer[void]
    tp_as_number: Pointer[void]
    tp_as_sequence: Pointer[void]
    tp_as_mapping: Pointer[void]
    tp_hash: Pointer[void]
    tp_call: Pointer[void]
    tp_str: Pointer[void]
    tp_getattro: Pointer[void]
    tp_setattro: Pointer[void]
    tp_as_buffer: Pointer[void]
    tp_flags: ULong
    tp_doc: Pointer[Char]
    tp_traverse: Pointer[void]
    tp_clear: Pointer[void]
    tp_richcompare: Pointer[void]
    tp_weaklistoffset: Py_ssize_t
    tp_iter: Pointer[void]
    tp_iternext: Pointer[void]
    tp_methods: Pointer[void]
    tp_members: Pointer[void]
    tp_getset: Pointer[void]
    tp_base: Pointer['PyTypeObject']
    tp_dict: Pointer[PyObject]
    tp_descr_get: Pointer[void]
    tp_descr_set: Pointer[void]
    tp_dictoffset: Py_ssize_t
    tp_init: Pointer[void]
    tp_alloc: Pointer[void]
    tp_new: Pointer[void]
    tp_free: Pointer[void]
    tp_is_gc: Pointer[void]
    tp_bases: Pointer[PyObject]
    tp_mro: Pointer[PyObject]
    tp_cache: Pointer[PyObject]
    tp_subclasses: Pointer[PyObject]
    tp_weaklist: Pointer[PyObject]
    tp_del: Pointer[void]
    tp_version_tag: UInt
    tp_finalize: Pointer[void]
    tp_vectorcall: Pointer[void]"""

