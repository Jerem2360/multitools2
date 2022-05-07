"""
Support header for dll importing.
"""

import ctypes
import sys
from typing import Any

__all__ = []


if sys.platform == 'win32':
    user32: Any = None  # real value is <extern module 'user32'>
    kernel32: Any = None  # real value is <extern module 'kernel32'>
    msvcrt: Any = None  # real value is <extern module 'msvcrt'>
    # ...

