import os
import pickle
import sys
import time

from multitools_2 import process


print("creating f() ...")
@process.Process
def f(proc=None):
    sys.stderr.write(repr(proc))
    time.sleep(2)
    pass

print(f)

print("created f() ...")
run = f()
print(run)
print("called f() ...")
time.sleep(3)

