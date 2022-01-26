import ctypes
from multitools import external


cint = ctypes.c_ulong(104)
Cint = external.Long[False, 'big', False].__from_c__(cint)

Iptr = external.Pointer[external.Long[False, 'big', False]].addressof(Cint)

print(Iptr, Iptr.value)

content = Iptr.contents()
print(content, content.value)

