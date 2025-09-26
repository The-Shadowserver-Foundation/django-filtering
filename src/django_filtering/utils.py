from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Q


# An arugment to the Q class
QArg = Tuple[str, Any]
QueryDataVar = List[str | Dict[str, Any]]


def construct_field_lookup_name(
    field_name: str,
    lookup: Optional[str] = None,
) -> str:
    """
    Given a field name and lookup, produce a valid argument query filter argument name.
    """
    lookup_expr = '__'.join(['', lookup]) if lookup else ''
    return f"{field_name}{lookup_expr}"


def construct_field_lookup_arg(
    field_name: str,
    value: Optional[Any] = None,
    lookup: Optional[str] = None,
) -> QArg:
    """
    Given a __query data__ structure make a field lookup value
    that can be used as an argument to ``Q``.
    """
    return (construct_field_lookup_name(field_name, lookup=lookup), value)


def deconstruct_query(
    query: Q,
) -> QueryDataVar:
    """
    Given a query (Q),
    deconstruct it into a __query data__ structure.
    """
    if len(query.children) >= 2:
        raise ValueError("Can only handle deconstruction of a single query value")
    field_lookup, value = query.children[0]
    split_info = field_lookup.split("__", 1)
    name = split_info.pop(0)
    if len(split_info) == 0:
        lookup = 'exact'
    else:
        lookup = split_info.pop()
    opts = {'value': value, 'lookup': lookup}
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
