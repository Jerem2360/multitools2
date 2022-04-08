"""
Constants for multitools._meta
"""

# attribute decorations names:
DEC_ABSTRACT = '__abstract__'
DEC_STATIC = '__static__'
DEC_CALLBACK = '__callback__'

# secret names:
SEC_DATA = '#00'
SEC_TEMP_INIT = '#01'
SEC_TEMP_NEW = '#02'
SEC_TEMP_GETATTRIBUTE = '#03'
SEC_VALUE = '#04'

# error format strings:
TYPE_ERROR_STR = "'{0}': Expected type '{1}', got '{2}' instead."
ATTR_ERROR_STR = "'{0}' has no attribute '{1}'."
POS_ARG_ERROR_STR = "'{0}' takes {1} positional arguments, but {2} were given."
ABS_OVERRIDE_ERROR_STR = "class '{0}' missing override for field '{1}'."

# multimeta flags:
FLAG_ABSTRACT = 1
FLAG_STATIC = 10

# other:
ITER = '__iter__'
FIELDS = '__fields__'
CLASSCELL = '__classcell__'
INIT = '__init__'
NEW = '__new__'
GETATTRIBUTE = '__getattribute__'
MRO = '__mro__'
CALL = '__call__'
NAME = '__name__'

