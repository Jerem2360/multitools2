from multitools.external import DllImport, Str, Library


@DllImport("C:/Windows/System32/msvcrt.dll")
def printf(data: Str) -> None: ...


printf("coucou")

