import ctypes


"""
Stuff that is common to all platforms
"""


typelist = {
    'c': ctypes.c_char,
    'h': ctypes.c_short,
    'H': ctypes.c_ushort,
    'i': ctypes.c_int,
    'I': ctypes.c_uint,
    'l': ctypes.c_long,
    'L': ctypes.c_ulong,
    'q': ctypes.c_longlong,
    'Q': ctypes.c_ulonglong,
    'f': ctypes.c_float,
    'd': ctypes.c_double,
    'n': ctypes.c_ssize_t,
    'N': ctypes.c_size_t,
    'P': ctypes.c_void_p,
}


rtypelist = dict((v, k) for k, v in typelist.items())


RESOURCE = ctypes.POINTER(ctypes.c_char)


class Resource(int):
    """
    A system resource either representing a string, or a number.
    Can hold paths, handles, names, numbers, ...
    """
    def as_char_p(self) -> ctypes.POINTER(ctypes.c_char) | None: ...


class DynamicResource(Resource):
    """
    A system resource that must be released after use.
    This class is dedicated to resources that need to be released
    after use. This includes files, libraries, memory spaces, ...
    """
    def release(self): ...

    def as_void_p(self):
        """
        In general, dynamic resources act as void* instances.
        That also is how they should be passed in to system calls.
        """
        return ctypes.cast(int(self), ctypes.c_void_p)

