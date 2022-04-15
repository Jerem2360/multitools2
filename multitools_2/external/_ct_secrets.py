import ctypes as _ct

# noinspection PyTypeChecker
SimpleCData = _ct.c_int.__mro__[-3]
# noinspection PyTypeChecker
PyCSimpleType = type(SimpleCData)
# noinspection PyTypeChecker
CData = _ct.c_int.__mro__[-2]

# noinspection PyTypeChecker
PyCArrayType = type(_ct.Array)
# noinspection PyTypeChecker
PyCPointerType = type(_ct.POINTER(_ct.c_int))
# noinspection PyTypeChecker
PyCStructType = type(_ct.Structure)
