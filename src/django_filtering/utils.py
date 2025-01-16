def merge_dicts(*args):
    if len(args) <= 1:
        return args[0] if len(args) else {}
    a, b, *args = args
    merger = {**a, **b}
    if len(args) == 0:
        return merger
    else:
        return merge_dicts(merger, *args)
