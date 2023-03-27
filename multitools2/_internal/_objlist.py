import gc
import sys
import time

import _ctypes


def _listobj(obj):
    res = []

    if not hasattr(obj, '__dict__'):
        return res

    for k, v in vars(obj).items():
        if (v not in gc.get_objects()) and (v not in res):
            res.append(v)
            if type(v) in (object, type):
                continue

            for n, o in vars(type(v)).items():
                if o not in res:
                    res.append(o)
    return res


def _static_objects():
    res = []

    for n, m in sys.modules.copy().items():
        for x in _listobj(m):
            if x not in res:
                res.append(x)

    return res


def _heap_objects():
    return gc.get_objects()


def _all_objects():
    res = _heap_objects()
    res.extend(_static_objects())
    tm = time.time()
    print('_all_objects(): done!', len(res))
    duration = time.time() - tm
    print(f"Time elapsed: {duration * 1000} ms")
    return res

