import sys


try:
    raise TypeError("Error")
except TypeError:
    print(sys.exc_info())

