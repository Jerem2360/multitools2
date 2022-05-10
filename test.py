import multiprocessing
import time

from multitools_2 import process


def activity(*args, **kwargs):
    start = time.localtime().tm_sec
    while time.localtime().tm_sec != (start + 3):
        pass


if __name__ == '__main__':
    proc = multiprocessing.Process(target=activity)
    proc.start()
    print(getattr(proc, '_popen'))

