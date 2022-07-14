from .._relay import MS_WINDOWS as _MS_WINDOWS


if _MS_WINDOWS:
    from ._win_processes import *
else:
    from ._posix_processes import *

