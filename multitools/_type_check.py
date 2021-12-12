

def typecheck(target, expected_type=object, target_name=None, expected_type_name=None, check_func=None):

    def default_check():
        return isinstance(target, expected_type)

    if check_func is None:
        check_func = default_check

    if not check_func():
        if expected_type_name is None:
            expected_type_name = expected_type.__name__

        target_txt = f"'{target_name}': "
        if target_name is None:
            target_txt = ""

        raise TypeError(f"{target_txt}Expected type '{expected_type_name}', got '{type(target).__name__}' instead.")

