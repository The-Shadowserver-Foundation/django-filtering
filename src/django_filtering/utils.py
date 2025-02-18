from typing import Any, Dict, List, Optional, Tuple

# An arugment to the Q class
QArg = Tuple[str, Any]
QueryDataVar = List[str | Dict[str, Any]]


def construct_field_lookup_name(
    field_name: str,
    lookup: Optional[str | List[str]] = None,
) -> str:
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


def construct_field_lookup_arg(
    field_name: str,
    value: Optional[Any] = None,
    lookup: Optional[str | List[str]] = None,
) -> QArg:
    """
    Given a __query data__ structure make a field lookup value
    that can be used as an argument to ``Q``.
    """
    return (construct_field_lookup_name(field_name, lookup=lookup), value)


def deconstruct_field_lookup_arg(
    field_lookup: str,
    value: Any,
    lookup: Optional[str | List[str]] = None,
) -> QueryDataVar:
    """
    Given a field name with lookup value,
    deconstruct it into a __query data__ structure.
    """
    name, *lookups = field_lookup.split("__")
    if not lookups:
        lookups = lookup
    elif len(lookups) == 1:
        lookups = lookups[0]

    opts = {'value': value}
    if lookups: opts['lookup'] = lookups
    return [name, opts]


def merge_dicts(*args):
    if len(args) <= 1:
        return args[0] if len(args) else {}
    a, b, *args = args
    merger = {**a, **b}
    if len(args) == 0:
        return merger
    else:
        return merge_dicts(merger, *args)
