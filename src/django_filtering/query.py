from django.db.models import Q as BaseQ


DEFAULT_LOOKUP = "iexact"


def construct_field_lookup_arg(field, value=None, lookup=DEFAULT_LOOKUP):
    """
    Given a __query data__ structure make a field lookup value
    that can be used as an argument to ``Q``.
    """
    sequence_types = (
        list,
        tuple,
    )
    is_lookup_seq = isinstance(lookup, sequence_types)
    lookup_expr = "__".join(lookup) if is_lookup_seq else lookup
    return (f"{field}__{lookup_expr}", value)


def deconstruct_field_lookup_arg(field, value):
    """
    Given a field name with lookup value,
    deconstruct it into a __query data__ structure.
    """
    field_name, *lookups = field.split("__")
    if len(lookups) == 1:
        lookups = lookups[0]

    return (field_name, {"lookup": lookups, "value": value})


class Q(BaseQ):
    @classmethod
    def from_query_data(cls, data, _is_root=True):
        key, value = data

        is_negated = False
        if key.upper() == "NOT":
            is_negated = True
            key, value = value

        valid_connectors = (
            cls.AND,
            cls.OR,
        )
        if key.upper() in valid_connectors:
            return cls(
                *(cls.from_query_data(v, _is_root=False) for v in value),
                _connector=key.upper(),
                _negated=is_negated,
            )
        else:
            if _is_root or is_negated:
                return cls(construct_field_lookup_arg(key, **value), _negated=is_negated)
            else:
                return construct_field_lookup_arg(key, **value)

    def to_query_data(self):
        if len(self.children) == 1:
            value = deconstruct_field_lookup_arg(*self.children[0])
        else:
            cls = self.__class__
            value = (
                self.connector.lower(),
                tuple(
                    child.to_query_data()
                    if isinstance(child, cls)
                    else deconstruct_field_lookup_arg(*child)
                    for child in self.children
                ),
            )

        if self.negated:
            value = ("not", value)
        return value
