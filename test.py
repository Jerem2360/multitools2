from multitools.interop import *


msvcrt = Library.load("msvcrt", callconv=__cdecl)

test = msvcrt[1280]

print(test(SSize_t(4)))

