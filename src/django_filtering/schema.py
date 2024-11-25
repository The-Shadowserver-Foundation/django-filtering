from .filters import Q


class FilterSchemaOptions:
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


class FilterSchemaMetaclass(type):
    def __new__(mcs, name, bases, attrs):
        new_class = super().__new__(mcs, name, bases, attrs)

        if bases == (BaseFilterSchema,):
            return new_class

        opts = new_class._meta = FilterSchemaOptions(getattr(new_class, "Meta", None))

        filters = {}
        for field in opts.model._meta.get_fields():
            if opts.match_field(field.name):
                filters[field.name] = {lookup_name for lookup_name in field.get_lookups().keys() if opts.match_field_lookup(field.name, lookup_name)}

        new_class.valid_filters = filters

        return new_class


class BaseFilterSchema:

    def __init__(self, query=None):
        if query and not isinstance(query, Q):
            query = Q.from_query_data(query)
        self.query = query


class FilterSchema(BaseFilterSchema, metaclass=FilterSchemaMetaclass):
    pass
