from .filters import Q


class FilterSchemaOptions:
    def __init__(self, options=None):
        self.model = getattr(options, "model", None)


class FilterSchemaMetaclass(type):
    def __new__(mcs, name, bases, attrs):
        new_class = super().__new__(mcs, name, bases, attrs)

        if bases == (BaseFilterSchema,):
            return new_class

        opts = new_class._meta = FilterSchemaOptions(getattr(new_class, "Meta", None))

        filters = {}
        for field in opts.model._meta.get_fields():
            filters[field.name] = [l for l in field.get_lookups().keys()]

        new_class.valid_filters = filters

        return new_class


class BaseFilterSchema:

    def __init__(self, query=None):
        if query and not isinstance(query, Q):
            query = Q.from_query_data(query)
        self.query = query


class FilterSchema(BaseFilterSchema, metaclass=FilterSchemaMetaclass):
    pass
