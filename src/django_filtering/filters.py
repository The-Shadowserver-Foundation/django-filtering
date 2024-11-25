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


class FilterSetOptions:
    def __init__(self, options=None):
        self.model = getattr(options, "model", None)
        self.filters = getattr(options, "filters", None)

    def _match_all(self) -> bool:
        return not self.filters or self.filters == '__all__'

    def match_field(self, field_name: str) -> bool:
        if self._match_all():
            return True
        return field_name in self.filters

    def match_field_lookup(self, field_name: str, lookup_name: str) -> bool:
        if self._match_all():
            return True
        return lookup_name in self.filters[field_name]


class FilterSetMetaclass(type):
    def __new__(mcs, name, bases, attrs):
        new_class = super().__new__(mcs, name, bases, attrs)

        if bases == (BaseFilterSet,):
            return new_class

        opts = new_class._meta = FilterSetOptions(getattr(new_class, "Meta", None))

        filters = {}
        for field in opts.model._meta.get_fields():
            if opts.match_field(field.name):
                filters[field.name] = {lookup_name for lookup_name in field.get_lookups().keys() if opts.match_field_lookup(field.name, lookup_name)}

        new_class.valid_filters = filters

        return new_class


class BaseFilterSet:

    def __init__(self, query=None):
        if query and not isinstance(query, Q):
            query = Q.from_query_data(query)
        self.query = query

    def get_queryset(self):
        return self._meta.model.objects.all()

    def filter_queryset(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        if self.query:
            queryset = queryset.filter(self.query)
        return queryset


class FilterSet(BaseFilterSet, metaclass=FilterSetMetaclass):
    pass
