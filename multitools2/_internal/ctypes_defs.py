"""
Type definitions for the C api structures, using ctypes.
Never use these directly. Use the ones defined in
multitools.interop instead.
"""

import ctypes
import sys

from . import *
from . import runtime, errors


# the PyObject typedef struct:
class _object(ctypes.Structure):
    if __trace_refs__:  # in debug builds, PyObject has 2 extra fields:
        _fields_ = (
            ("_ob_next", ctypes.py_object),
            ("_ob_prev", ctypes.py_object),
            ("ob_refcnt", ctypes.c_ssize_t),
            ("ob_type", ctypes.c_void_p),
        )
    else:
        _fields_ = (
            ("ob_refcnt", ctypes.c_ssize_t),
            ("ob_type", ctypes.c_void_p),
        )
_object_p = ctypes.POINTER(_object)  # PyObject*


# the PyVarObject typedef struct:
class _varobject(ctypes.Structure):
    _fields_ = (
        ("ob_base", _object),
        ("ob_size", ctypes.c_ssize_t),
    )
_varobject_p = ctypes.POINTER(_varobject)  # PyVarObject*


# the PyTypeObject typedef struct:
class _typeobject(ctypes.Structure):
    _fields_ = (
        ("ob_base", _varobject),
        ("tp_name", ctypes.c_char_p),
        ("tp_basicsize", ctypes.c_ssize_t),
        ("tp_itemsize", ctypes.c_ssize_t),
        ("tp_dealloc", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_vectorcall_offset", ctypes.c_ssize_t),
        ("tp_getattr", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_setattr", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_as_async", ctypes.c_void_p),
        ("tp_repr", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_as_number", ctypes.c_void_p),
        ("tp_as_sequence", ctypes.c_void_p),
        ("tp_as_mapping", ctypes.c_void_p),
        ("tp_hash", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_call", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_str", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_getattro", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_setattro", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_as_buffer", ctypes.c_void_p),
        ("tp_flags", ctypes.c_ulong),
        ("tp_doc", ctypes.c_char_p),
        ("tp_traverse", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_clear", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_richcompare", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_weaklistoffset", ctypes.c_ssize_t),
        ("tp_iter", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_iternext", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_methods", ctypes.c_void_p),
        ("tp_members", ctypes.c_void_p),
        ("tp_getset", ctypes.c_void_p),
        ("tp_base", ctypes.c_void_p),
        ("tp_dict", ctypes.py_object),
        ("tp_descr_get", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_descr_set", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_dictoffset", ctypes.c_ssize_t),  # this is actually a function pointer
        ("tp_init", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_alloc", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_new", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_free", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_is_gc", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_bases", ctypes.py_object),
        ("tp_mro", ctypes.py_object),
        ("tp_cache", ctypes.py_object),
        ("tp_subclasses", ctypes.py_object),
        ("tp_weaklist", ctypes.py_object),
        ("tp_del", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_version_tag", ctypes.c_uint),
        ("tp_finalize", ctypes.c_void_p),  # this is actually a function pointer
        ("tp_vectorcall", ctypes.c_void_p),  # this is actually a function pointer
    )
_typeobject_p = ctypes.POINTER(_typeobject)  # PyTypeObject*



if MS_WIN32:
    _THREAD_TERMINATE = 0x0001
    _THREAD_QUERY_INFORMATION = 0x0040
    _THREAD_GET_CONTEXT = 0x0008
    _SYNCHRONIZE = 0x00100000

    _INFINITE = 0xFFFFFFFF

    _STILL_ACTIVE = 259

    _WAIT_ABANDONED = 0x00000080
    _WAIT_OBJECT_0 = 0
    _WAIT_TIMEOUT = 0x00000102
    _WAIT_FAILED = 0xFFFFFFFF

    _ERROR_INVALID_HANDLE = 6
    _ERROR_BAD_THREADID_ADDR = 159

    from ctypes.wintypes import HANDLE, DWORD, BOOL
    import _winapi

    ctypes.windll.kernel32.OpenThread.argtypes = (DWORD, BOOL, DWORD)
    ctypes.windll.kernel32.OpenThread.restype = HANDLE

    ctypes.windll.kernel32.WaitForSingleObject.argtypes = (HANDLE, DWORD)
    ctypes.windll.kernel32.WaitForSingleObject.restype = DWORD

    ctypes.windll.kernel32.GetExitCodeThread.argtypes = (HANDLE, ctypes.POINTER(DWORD))
    ctypes.windll.kernel32.GetExitCodeThread.restype = BOOL

    def open_thread(tid, inherit_handle=False):
        """
        Open the thread given by tid, and return a handle to it.
        This function only has purpose on Windows.
        """
        access = _THREAD_TERMINATE | _THREAD_QUERY_INFORMATION | _THREAD_GET_CONTEXT | _SYNCHRONIZE
        handle = ctypes.windll.OpenThread(DWORD(access), BOOL(int(inherit_handle)), DWORD(tid))
        if not handle:
            msg = ctypes.FormatError()
            code = ctypes.GetLastError()
            if code == _ERROR_INVALID_HANDLE:
                raise errors.InvalidHandleError("Invalid handle.") from errors.configure(1)
            if code == _ERROR_BAD_THREADID_ADDR:
                raise ValueError("Unknown thread id.") from errors.configure(1)
            raise OSError(None, msg, runtime.call_stack[1].f_code.co_filename, code) from errors.configure(1)
        return tid, _Handle(handle)

    def wait_thread(tid, handle, timeout=None):
        """
        Wait for the given thread to terminate.
        If timeout is None, wait until the thread terminates and return True.
        If timeout is given, wait for maximum 'timeout' seconds. Then,
        return if the process has effectively terminated.
        """
        if handle is None:
            try:
                _i, handle = open_thread(tid, True)
            except BaseException as e:
                raise e from errors.configure(1)

        timeout_ms = _INFINITE if timeout is None else int(timeout * 1000)
        result = ctypes.windll.kernel32.WaitForSingleObject(HANDLE(handle), DWORD(timeout_ms))
        if result == _WAIT_OBJECT_0:
            return True
        if result == _WAIT_ABANDONED:
            raise RuntimeError("Invalid thread state.") from errors.configure(1)
        if result == _WAIT_TIMEOUT:
            return False
        if result == _WAIT_FAILED:
            msg = ctypes.FormatError()
            code = ctypes.GetLastError()
            if code == _ERROR_INVALID_HANDLE:
                raise errors.InvalidHandleError("Invalid handle.") from errors.configure(1)
            if code == _ERROR_BAD_THREADID_ADDR:
                raise ValueError("Unknown thread id.") from errors.configure(1)
            raise OSError(None, msg, runtime.call_stack[1].f_code.co_filename, code) from errors.configure(1)
        return False

    def exitcode_thread(tid, handle):
        """
        Return a thread's exit status. This is None for threads that are still
        running.
        """
        if handle is None:
            try:
                _i, handle = open_thread(tid, True)
            except BaseException as e:
                raise e from errors.configure(1)

        exitcode_p = ctypes.cast(0, ctypes.POINTER(DWORD))
        res = ctypes.windll.kernel32.GetExitCodeThread(DWORD(handle), exitcode_p)
        if not res:
            msg = ctypes.FormatError()
            code = ctypes.GetLastError()
            if code == _ERROR_INVALID_HANDLE:
                raise errors.InvalidHandleError("Invalid handle.") from errors.configure(1)
            if code == _ERROR_BAD_THREADID_ADDR:
                raise ValueError("Unknown thread id.") from errors.configure(1)
            raise OSError(None, msg, runtime.call_stack[1].f_code.co_filename, code) from errors.configure(1)

        exitcode = exitcode_p.contents
        if exitcode.value == _STILL_ACTIVE:
            return
        return exitcode.value


    class _Handle(int):
        def __del__(self):
            try:
                _winapi.CloseHandle(int(self))
            except:
                pass

else:

    def open_thread(tid, **kwargs):
        return tid, None

    def wait_thread(tid, handle, timeout=None): ...




