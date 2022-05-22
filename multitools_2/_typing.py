from typing import Generic


TYPE_ERR_STR = "Expected type '{0}', got '{1}' instead."


def type_check(values, *types):
    if not isinstance(values, tuple):
        raise TypeError(f"'type_check():values': expected type 'tuple', got '{type(values).__name__}' instead.") from None

    if len(values) != len(types):
        raise ValueError("type_check(): There must be as many values as types.") from None

    for i in range(len(values)):

        val = values[i]
        tp = types[i]

        res = _check(val, tp)
        match res[0]:
            case -1:
                if callable(tp):
                    ch = tp(val)
                    if isinstance(ch, Exception):
                        raise ch
                    continue
                raise TypeError("type_check(): type arguments must be 'type | tuple[type | Callable] | Callable'.") from None
            case 0:
                # raise TypeError(f"Expected type '{res[1]}', got '{type(val).__name__}' instead.")
                raise TypeError(TYPE_ERR_STR.format(res[1], type(val).__name__)) from None
            case _:
                continue


def _check(val, tp):
    tp_type = type(tp).__name__
    if isinstance(tp, type):
        tp_type = type(tp).__mro__[-2].__name__ if len(type(tp).__mro__) >= 2 else type(tp).__mro__[-1]

    match tp_type:

        case "NoneType":
            return (val is None), "NoneType"
        case "tuple":
            real_types = []
            tp_nm = ""
            for t in tp:
                if t is None:
                    real_types.append(type(None))
                    tp_nm += "NoneType, "
                    continue
                if isinstance(t, type):
                    if hasattr(t, '__origin__'):
                        real_types.append(t.__origin__)
                        tp_nm += f"{t.__origin__.__name__}, "
                        continue
                    real_types.append(t)
                    tp_nm += f"{t.__name__}, "
                    continue
                return -1
            tp_nm = tp_nm.removesuffix(', ')
            return int(isinstance(val, tuple(real_types))), f"Union[{tp_nm}]"

        case "type":
            if hasattr(tp, '__origin__'):
                return isinstance(val, tp.__origin__), tp.__origin__.__name__
            return int(isinstance(val, tp)), tp.__name__
        case _:
            return -1, ""

