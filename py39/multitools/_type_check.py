

def typecheck(target, expected_types=(object,), target_name=None, expected_type_name=None, check_func=None):

    def default_check():
        result = False
        for tp in expected_types:
            if not isinstance(tp, type):
                raise TypeError(f"'expected_types': expected type 'tuple[type]', got 'tuple[{type(tp).__name__}]' instead.")
            if isinstance(target, tp):
                result = True
                break

        return result

    if not isinstance(expected_types, tuple):
        raise TypeError(f"'expected_types': expected type 'tuple[type]', got '{type(expected_types).__name__}' instead.")

    if not isinstance(target_name, str):
        raise TypeError(f"'target_name': expected type 'str', got '{type(target_name).__name__}' instead.")

    if not isinstance(expected_type_name, (str, type(None))):
        raise TypeError(f"'expected_type_name': expected type 'str', got '{type(expected_type_name).__name__}' instead.")

    if not (isinstance(check_func, type(None)) or callable(check_func)):
        raise TypeError(f"'check_func': expected type 'Callable', got '{type(check_func).__name__}' instead.")

    if len(expected_types) == 0:
        expected_types = (object,)

    if check_func is None:
        check_func = default_check

    if not check_func():
        if expected_type_name is None:
            if len(expected_types) == 1:
                expected_type_name = expected_types[0].__name__
            else:
                typenames = str(list(expected_types))
                expected_type_name = f"Union{typenames}"

        target_txt = f"'{target_name}': "
        if target_name is None:
            target_txt = ""

        raise TypeError(f"{target_txt}Expected type '{expected_type_name}', got '{type(target).__name__}' instead.")

