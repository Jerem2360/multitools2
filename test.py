import ctypes

from multitools_2.external import *


@DllImport("msvcrt.dll")
def printf(data: Pointer[typedefs.Char]) -> typedefs.Int: ...


c = typedefs.Char("a")
c_p = Pointer[typedefs.Char].addressof(c)
print(c_p.deref())

printf(c_p)


