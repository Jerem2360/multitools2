import sys
if sys.version_info.major != 3:
    raise NotImplementedError("This library only supports python 3.")
if sys.platform != "win32":
    raise NotImplementedError("This library only supports the Windows platform.")


if sys.version_info.minor >= 10:
    from ._meta_new import *
else:
    from ._meta_old import *


__all__ = [
    "ClassData",
    "AbstractMethodDescriptor",
    "MultiMeta",
]

