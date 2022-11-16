from multitools.interop import *

msvcrt = Library.load('msvcrt.dll')

@dllimport(msvcrt)
def printf(msg: Array[Char, 3]) -> None: ...

data = Array[Char, 3](Char(b'a'), Char(b'b'), Char(b'c'))


printf(data)


