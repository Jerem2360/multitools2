import _thread
import os
import sys
import time

from multitools2._internal import tstate, threadrun

# print(tstate.main_thread.alive)

def act(state):
    state._begin()
    time.sleep(1)
    print('thread:', state.call_stack)
    state._end()


th = threadrun.start(act, ())
# print('main:', th)
time.sleep(2)
# print(_thread.get_native_id())
print(tstate._threads)

