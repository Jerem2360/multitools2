import _thread
import os

from .._const import *
from .._shared_memory import SharedDict
if MS_WINDOWS:
    from .._win32 import getpid as _getpid
else:
    from os import getpid as _getpid


_current_proc_threads = []  # per-process


# if we are the main process, create our shared memory blocks, otherwise just open them.
if _getpid() == MAIN_PROCESS_ID:

    _all_processes = SharedDict.from_dict({'count': 0})  # per-process hierarchy
    _all_python_processes = SharedDict(create=True)  # per-process hierarchy

else:
    _all_procs_name = os.environ.get(ENV_PROCS, '<unknown>')
    _all_py_procs_name = os.environ.get(ENV_PY_PROCS, '<unknown>')
    if '<unknown>' in (_all_procs_name, _all_py_procs_name):
        raise SystemError(f"One or more environment variables were missing.\nEnvironment variables were:\n{os.environ}")
    _all_processes = SharedDict(name=_all_procs_name, create=False)
    _all_python_processes = SharedDict(name=_all_py_procs_name, create=False)


class _NullHVal_t:
    pass


NUL_HVal = _NullHVal_t()


class DataBaseElement:
    @classmethod
    def create(cls, db):
        if 'count' in db:
            lid = db['count']
        else:
            lid = db['count'] = 0
        db['count'] += 1
        # print('before:', db)
        db[lid] = {}
        # print('after:', db)
        return cls(db, lid)

    @classmethod
    def find(cls, db, **hints):
        for lid, elem in db.items():
            # print(hints, elem)
            if not isinstance(elem, (dict, SharedDict)):
                continue
            err = False
            for hname, hval in hints.items():
                if hname not in elem:
                    err = True
                    break
                if hval == NUL_HVal:
                    continue
                if elem[hname] != hval:
                    err = True
                    break
            if not err:
                return cls(db, lid)

    def __init__(self, db, lid):
        self._database = db
        self._local_id = lid
        self._closed = False

    def _check_db(self):
        if not self._closed:
            try:
                # print('try', self._database, self._local_id, self._database[self._local_id])
                _ = self._database[self._local_id]
            except KeyError:
                self._closed = True

    def __getitem__(self, item):
        self._check_db()
        if not self._closed:
            return self._database[self._local_id][item]
        raise ValueError("Database element no longer exists.")

    def __setitem__(self, key, value):
        self._check_db()
        # print('setitem', key, value)
        # print(self._database[self._local_id])
        if not self._closed:
            # self._database[self._local_id][key] = value
            data = self._database[self._local_id]
            data[key] = value
            self._database[self._local_id] = data
            return
        raise ValueError("Database element no longer exists.")

    def __delitem__(self, key):
        self._check_db()
        if not self._closed:
            # del self._database[self._local_id][key]
            data = self._database[self._local_id]
            del data[key]
            self._database[self._local_id] = data
            return
        raise ValueError("Database element no longer exists.")

    def __getattr__(self, item):
        self._check_db()
        if not self._closed:
            return getattr(self._database, item)
        raise ValueError("Database element no longer exists.")

    def __contains__(self, item):
        self._check_db()
        if not self._closed:
            return item in self._database[self._local_id]
        raise ValueError("Database element no longer exists.")

    def remove(self):
        if not self._closed:
            try:
                del self._database[self._local_id]
            except:
                pass
            self._closed = True

    @property
    def id(self):
        return self._local_id

    def __repr__(self):
        return f'DataBaseElement({self._database}, {self._local_id})'

