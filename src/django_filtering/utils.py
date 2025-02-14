from typing import List, Optional

def construct_field_lookup_name(field_name, lookup: Optional[str | List[str]] = None) -> str:
    """
    Given a field name and lookup, produce a valid argument query filter argument name.
    """
    sequence_types = (
        list,
        tuple,
    )
    lookup_expr = ''
    if lookup is not None:
        is_lookup_seq = isinstance(lookup, sequence_types)
        lookup_expr = "__".join(['', *lookup] if is_lookup_seq else ['', lookup])
    return f"{field_name}{lookup_expr}"


def construct_field_lookup_arg(field, value=None, lookup=None):
    """
    Given a __query data__ structure make a field lookup value
    that can be used as an argument to ``Q``.
    """
    return (construct_field_lookup_name(field, lookup=lookup), value)


def merge_dicts(*args):
    if len(args) <= 1:
        return args[0] if len(args) else {}
    a, b, *args = args
    merger = {**a, **b}
    if len(args) == 0:
        return merger
    else:
        return merge_dicts(merger, *args)
