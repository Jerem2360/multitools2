import pickle


def find_name(name, locals_):
    if name in globals():
        return globals()[name]
    if name in locals_:
        return locals_[name]
    import builtins
    if hasattr(builtins, name):
        return getattr(builtins, name)
    return None


x = 10


def f(y=0):
    print("coucou", x, None)


func_pickle = pickle.dumps(f)


new_f = pickle.loads(func_pickle)

f_required = {}

for name in f.__code__.co_names:
    obj = find_name(name, locals())
    if obj is not None:
        f_required[name] = obj

print(new_f, f.__code__.co_names, f_required)

other_f = type(f)(f.__code__, f_required, name='f2', argdefs=f.__defaults__)
other_f()

