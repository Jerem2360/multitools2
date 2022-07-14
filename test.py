import io
import os
import sys
import time
import pickle
import _thread


from multitools_2.runtime import _process2

def f(*args, **kwargs): ...

test1 = _process2.Process('echo')
test2 = _process2.Process(f)
test3 = _process2.Process()
# print(test3.pid)
# test4 = _process2.Process(1234555666667)
print(test2._build_code((0, 1, 3), (), {}))

print(test1)
print(test2)
print(test3)


