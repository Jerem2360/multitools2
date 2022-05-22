import sys
import pickle
import types


def _get_sysmodules_names():
    names = []
    for name in sys.modules.keys():
        names.append(name)
    return tuple(names)


def pickle_function(function, name: str):
    needed_globals = {}
    for _name in function.__code__.co_names:
        if (_name not in dir(sys.modules['builtins'])) and (_name in function.__globals__):
            try:
                needed_globals[_name] = pickle.dumps(function.__globals__[_name]) if function.__globals__[_name] is not None else None
            except:
                needed_globals[_name] = None

    result = {
        f'{name}:name': function.__name__,
        f'{name}:defaults': function.__defaults__,
        f'{name}:closure': function.__closure__,
        f'{name}:co_argcount': function.__code__.co_argcount,
        f'{name}:co_kwonlyargcount': function.__code__.co_kwonlyargcount,
        f'{name}:co_nlocals': function.__code__.co_nlocals,
        f'{name}:co_stacksize': function.__code__.co_stacksize,
        f'{name}:co_flags': function.__code__.co_flags,
        f'{name}:co_code': function.__code__.co_code,
        f'{name}:co_consts': function.__code__.co_consts,
        f'{name}:co_names': function.__code__.co_names,
        f'{name}:co_varnames': function.__code__.co_varnames,
        f'{name}:co_filename': function.__code__.co_filename,
        f'{name}:co_name': function.__code__.co_name,
        f'{name}:co_firstlineno': function.__code__.co_firstlineno,
        f'{name}:co_lnotab': function.__code__.co_lnotab,
        f'{name}:co_freevars': function.__code__.co_freevars,
        f'{name}:co_cellvars': function.__code__.co_cellvars,
        f'{name}:globals': needed_globals,
        f'{name}:sys_modules': _get_sysmodules_names(),
    }
    if sys.version_info >= (3, 8):
        result[f'{name}:co_posonlyargcount'] = function.__code__.co_posonlyargcount
    return result


def unpickle_function(state, name):
    import sys

    code_args = [
        state[f'{name}:co_argcount'],
        state[f'{name}:co_kwonlyargcount'],
        state[f'{name}:co_nlocals'],
        state[f'{name}:co_stacksize'],
        state[f'{name}:co_flags'],
        state[f'{name}:co_code'],
        state[f'{name}:co_consts'],
        state[f'{name}:co_names'],
        state[f'{name}:co_varnames'],
        state[f'{name}:co_filename'],
        state[f'{name}:co_name'],
        state[f'{name}:co_firstlineno'],
        state[f'{name}:co_lnotab'],
        state[f'{name}:co_freevars'],
        state[f'{name}:co_cellvars'],
    ]
    if sys.version_info >= (3, 8):
        code_args.insert(1, state[f'{name}:co_posonlyargcount'])


    function_code = types.CodeType(*code_args)
    function = types.FunctionType(
        function_code,
        globals(),
        state[f'{name}:name'],
        state[f'{name}:defaults'],
        state[f'{name}:closure'],
    )

    glob = state[f'{name}:globals']
    for _name, value in glob.items():
        if (_name not in globals()) and (_name in function.__code__.co_names):
            globals()[_name] = pickle.loads(value) if value is not None else None

    for required_module in state[f'{name}:sys_modules']:
        if required_module in function.__code__.co_names:
            if required_module not in sys.modules:
                sys.modules[required_module] = __import__(required_module)
            if (required_module not in globals()) or (globals()[required_module] is None):
                globals()[required_module] = sys.modules[required_module]

    return function

