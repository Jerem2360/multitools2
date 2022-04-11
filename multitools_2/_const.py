import sys
import os


# generic constants:
GLOBAL_NAME = 'multitools_2'

# submodule names:
MODNAME_EXTERNAL = GLOBAL_NAME + '.external'

# path-related constants
OS_PATHSEP = os.sep
STD_PATHSEP = '/'

# dll importing constants:
DLL_EXTENSION = '.dll' if sys.platform == 'win32' else '.so'
DLL_PARENT_MODULE_NAME = "<dll loader module>"
DLLIMPORT_FROM_NAME = GLOBAL_NAME + '.dll'

