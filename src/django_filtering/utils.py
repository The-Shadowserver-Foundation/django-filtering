from typing import Any

from django.db.models import Field, Q
from django.utils.text import capfirst


# An arugment to the Q class
QArg = tuple[str, Any]
QueryDataVar = list[str | dict[str, Any]]


def construct_field_lookup_name(
    field_name: str,
    lookup: str | None = None,
) -> str:
    """
    Given a field name and lookup, produce a valid argument query filter argument name.
    """
    lookup_expr = '__'.join(['', lookup]) if lookup else ''
    return f"{field_name}{lookup_expr}"


def construct_field_lookup_arg(
    field_name: str,
    value: Any | None = None,
    lookup: str | None = None,
) -> QArg:
    """
    Given a __query data__ structure make a field lookup value
    that can be used as an argument to ``Q``.
    """
    return (construct_field_lookup_name(field_name, lookup=lookup), value)


def deconstruct_field_lookup_arg(
    field_lookup: str,
    value: Any,
    lookup: str | list[str] | None = None,
) -> QueryDataVar:
    """
    Given a field name with lookup value,
    deconstruct it into a __query data__ structure.
    """
    split_info = field_lookup.split("__", 1)
    name = split_info.pop(0)
    if len(split_info) == 0:
        lookup = 'exact'
    else:
        lookup = split_info.pop()
    opts = {'value': value, 'lookup': lookup}
    return [name, opts]


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


def model_field_label(field: Field) -> str:
    if field.is_relation:
        label = field.related_model._meta.verbose_name
    else:
        label = field.verbose_name
    return capfirst(label)
