from django.db.models import Q as BaseQ, QuerySet

from .schema import JSONSchema, FilteringOptionsSchema


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
                lookups = {lookup_name for lookup_name in field.get_lookups().keys() if opts.match_field_lookup(field.name, lookup_name)}
                # Coerce to list for JSON encoding and sort for idempotence
                lookups = sorted(list(lookups))
                filters[field.name] = lookups

        new_class.valid_filters = filters

        return new_class


class InvalidQueryData(Exception):
    pass


class InvalidFilterSet(Exception):
    pass


class BaseFilterSet:

    def __init__(self, query_data=None):
        self.query_data = query_data
        # Initialize the rendered query state
        # This represents the data as native Q objects
        self._query = None
        # Initialize the errors state, to be called by is_valid()
        self._errors = None
        # Create the json-schema for validation
        # Note, this is a public variable because it can be made public for frontend validation.
        self.json_schema = JSONSchema(self)
        # Create the filtering options schema
        # to provide the frontend with the available filtering options.
        self.filtering_options_schema = FilteringOptionsSchema(self)

    def get_queryset(self):
        return self._meta.model.objects.all()

    def filter_queryset(self, queryset=None) -> QuerySet:
        if not self.is_valid:
            raise InvalidFilterSet(
                "The query is invalid! "
                "Hint, check `is_valid` before running `filter_queryset`."
            )
        if queryset is None:
            queryset = self.get_queryset()
        if self.query:
            queryset = queryset.filter(self.query)
        return queryset

    @property
    def is_valid(self) -> bool:
        """Property used to check trigger and check validation."""
        if self._errors is None:
            self.validate()
        return not self._errors

    @property
    def errors(self):
        """A list of validation errors. This value is populated when there are validation errors."""
        return self._errors

    @property
    def query(self) -> Q:
        """Q object derived from query data. Only available after validation."""
        return self._query

    def validate(self) -> None:
        """Check the given query data contains valid fields and lookups."""
        # FIXME I'd like the validate the contents on both the frontend and backend
        #       using json-schema. A solution is somewhat working, but needs further
        #       testing in order to make it a viable solution.
        # For the time being validate based on field and lookup name.
        # Note this solution is not meant to handle operators at depth.
        # It assumes a single top-level operator (i.e. AND or OR) with
        # an array of filter criteria.
        self._errors = {}
        if self.query_data and not isinstance(self.query_data, Q):
            try:
                operator = self.query_data[0]
            except (IndexError, KeyError, TypeError):
                raise InvalidQueryData("invalid format")
            if operator.lower() not in ('and', 'or',):
                self._errors['top_level_operator'] = [f"invalid operator '{operator.lower()}' used"]
            for filter_name, details in self.query_data[1]:
                if filter_name not in self.valid_filters:
                    self._errors.setdefault(filter_name, [])
                    self._errors[filter_name].append('invalid filter')
                    continue
                elif details['lookup'] not in self.valid_filters[filter_name]:
                    self._errors.setdefault(filter_name, [])
                    self._errors[filter_name].append('invalid filter lookup')
            if not self._errors:
                # Translate to Q objects
                self._query = Q.from_query_data(self.query_data)


class FilterSet(BaseFilterSet, metaclass=FilterSetMetaclass):
    pass
