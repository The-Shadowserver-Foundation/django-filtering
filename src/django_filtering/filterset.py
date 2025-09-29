import warnings
from functools import cached_property
from typing import Any

import jsonschema
from django.conf import settings
from django.db.models import Q, QuerySet

from .filters import Filter
from .schema import JSONSchema, FilteringOptionsSchema


class MetadataException(Exception):
    """
    Base exception for Metadata exceptions
    """


class RequiredMetadataError(MetadataException):
    """
    Raised when a Meta class option is undefined and required.
    """


class Metadata:
    """
    FilterSet metadata
    This class is used to instantiate ``FilterSet._meta``.
    """

    PUBLIC_KEYWORD_ARGS = (
        'abstract',
        'model',
        'filters',
    )
    PRIVATE_KEYWORD_ARGS = (
        '_parents',
        '_declared_filters',
    )
    KEYWORD_ARGS = PUBLIC_KEYWORD_ARGS + PRIVATE_KEYWORD_ARGS

    def __init__(self, **kwargs):
        self.parents = kwargs['_parents']
        self.is_abstract = kwargs.get('abstract', False)
        self.model = kwargs.get("model", None)
        if self.model is None and not self.is_abstract:
            if len(self.parents) >= 1 and self.parents[0]._meta.model is not None:
                self.model = self.parents[0]._meta.model
            else:
                raise RequiredMetadataError("`model` is required.")
        self.declared_filters = kwargs.get('_declared_filters', {})
        # TODO: Create filters from `filters` meta option
        self._filters = self.declared_filters

    @cached_property
    def filters(self) -> dict[str, Filter]:
        filters = self._filters.copy()
        for parent in reversed(self.parents):
            for name, filter in parent._meta.filters.items():
                if name not in filters:
                    filters[name] = filter
        return filters

    def get_filter(self, name: str) -> Filter:
        return self.filters[name]

    @property
    def sticky_filters(self) -> dict[str, Filter]:
        return {k: v for k, v in self.filters.items() if v.is_sticky}


class FilterSetType(type):
    def __new__(mcs, name, bases, attrs):
        # Capture the meta configuration
        Meta = attrs.pop('Meta', None)
        if Meta is None:
            meta_opts = {}
        else:
            meta_opts = {k: v for k, v in Meta.__dict__.items() if not k.startswith('_')}

        if not bases:
            # Treat base FilterSet as abstract
            meta_opts['abstract'] = True
        meta_opts['_parents'] =  [b for b in bases if isinstance(b, FilterSetType)]

        # Pull out filters from the class definition
        meta_opts['_declared_filters'] = {
            attr_name: attrs.pop(attr_name).bind(attr_name)
            for attr_name, filter in list(attrs.items())
            if isinstance(filter, Filter)
        }

        # Declare meta class options for runtime usage
        try:
            attrs['_meta'] = Metadata(**meta_opts)
        except MetadataException as exc:
            if isinstance(exc, RequiredMetadataError):
                raise ValueError(
                    f"Creation of {name} errored due "
                    f"to a missing required metadata property: {exc.args[0]}"
                )

        # Create the new class
        return super().__new__(mcs, name, bases, attrs)


class InvalidQueryData(Exception):
    pass


class InvalidFilterSet(Exception):
    pass


class FilterSet(metaclass=FilterSetType):
    valid_connectors = (
        Q.AND,
        Q.OR,
    )

    def __init__(self, query_data=None):
        self.query_data = [] if query_data is None else query_data
        # Initialize the errors state, to be called by is_valid()
        self._errors = None
        # Create the json-schema for validation
        # Note, this is a public variable because it can be made public for frontend validation.
        self.json_schema = JSONSchema(self)
        # Create the filtering options schema
        # to provide the frontend with the available filtering options.
        self.filtering_options_schema = FilteringOptionsSchema(self)

    def get_default_queryset(self):
        return self._meta.model.objects.all()

    @cached_property
    def filters(self) -> list[Filter]:
        return list(self._meta.filters.values())

    def _get_filter(self, name: str) -> Filter:
        """
        Get the filter object by name
        """
        return self._meta.filters[name]

    @cached_property
    def sticky_filters(self) -> list[Filter]:
        return [f for f in self.filters if f.is_sticky]

    def filter_queryset(self, queryset=None) -> QuerySet:
        if queryset is None:
            queryset = self.get_default_queryset()

        if not self.is_valid:
            raise InvalidFilterSet(
                "The query is invalid! "
                "Hint, check `is_valid` before running `filter_queryset`.\n"
                f"Errors:\n{self._errors}"
            )

        query = self.get_query(queryset)
        if query:
            queryset = queryset.filter(query)
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

    def _make_json_schema_validator(self, schema):
        cls = jsonschema.validators.validator_for(schema)
        cls.check_schema(schema)  # XXX
        if settings.DEBUG:
            try:
                cls.check_schema(schema)
            except jsonschema.SchemaError:
                raise RuntimeError("The generated schema is invalid. This is a bug.")

        return cls(schema)

    def validate(self) -> None:
        """
        Check the given query data contains valid syntax, fields and lookups.

        Errors will be available in the ``errors`` property.
        If the property is empty, there were no errors.

        Use the ``is_valid`` property to call this method.
        """
        self._errors = []

        # Validates both the schema and the data
        validator = self._make_json_schema_validator(self.json_schema.schema)
        for err in validator.iter_errors(self.query_data):
            # TODO We can provide better detail than simply echoing
            #      the exception details. See jsonschema.exceptions.best_match.
            self._errors.append({
                'json_path': err.json_path,
                'message': err.message,
            })

    def get_query(self, queryset) -> Q | None:
        """Q object derived from query data. Only available after validation."""
        q = self._transmute(self.query_data, queryset)
        q = self._apply_sticky_filters(q, queryset)
        return q

    def make_context(self, filter, queryset=None) -> dict[str, Any]:
        if queryset is None:
            queryset = self.get_default_queryset()
        return {
            'filterset': self,
            'queryset': queryset,
            'filter': filter,
        }

    def _transmute(
        self,
        query_data: None | list,
        queryset: QuerySet,
        _is_root: bool = True
    ) -> Q | None:
        """
        Transmute the given query data to a ``Q`` object.
        """
        if not query_data:
            return None

        key, value = query_data

        is_negated = False
        if key.upper() == "NOT":
            is_negated = True
            # Unwrap the negated grouping
            key, value = value

        if key.upper() in self.valid_connectors:
            connector = key.upper()
            q = Q.create(connector=connector)
            # Recurively build query tree
            for v in value:
                q_child = self._transmute(v, queryset=queryset, _is_root=False)
                if not q_child: continue
                q = q._combine(q_child, connector)
            q.negated = is_negated
        else:
            context = self.make_context(filter=self._get_filter(key), queryset=queryset)
            q = self.call_transmuter(value, context)
            if q and (_is_root or is_negated):
                q = Q.create(q.children, negated=is_negated)
        return q

    def call_transmuter(self, criteria: dict[str, Any], context: dict[str, Any]) -> Q | None:
        """
        Obtains the transmuter function given contextual information.
        Returns a callable that will transmute the context into a Q instance.

        Definition of a custom transmuter can be done by creating a method on the `FilterSet`
        named `transmute_<filter>` and/or more specific to the lookup as `transmute_<filter>__<lookup...>`.
        These transmuter methods are intended to provide the developer with
        an easy way to override the default transmute logic of the filter.
        """
        # FIXME The lookup is optional, but we don't have a fully formed case where
        #       the default lookup information is not available.
        lookup = criteria.get('lookup', '')
        if isinstance(lookup, list):
            lookup = '__'.join(lookup)

        filter = context['filter']
        funcs = [
            getattr(self, f"transmute_{filter.name}__{lookup}", None),
            getattr(self, f"transmute_{filter.name}", None),
            filter.transmute,
        ]
        transmuter = [f for f in funcs if f is not None][0]
        return transmuter(criteria, context=context)

    def _apply_sticky_filters(self, q, queryset):
        """
        Apply sticky filters to the query filters.

        Sticky filters are applied when the user provided query data
        does not contain the sticky filter
        or when the sticky or default value have been set to anything other than
        the solvent value.
        """
        # Define the set of filter names used in the current query data.
        if len(self.query_data) >= 2:
            query_data_filter_names = {key for key, _ in self.query_data[1]}
        else:
            # Empty set because no query data was provided.
            query_data_filter_names = set([])

        sticky_q = Q()
        for sf in self.sticky_filters:
            if sf.name not in query_data_filter_names:
                # Anding the sticky filter's default Q
                sticky_q &= sf.get_sticky_Q(context=self.make_context(filter=sf))

        return sticky_q & q if q else sticky_q


def filterset_factory(model, base_cls=FilterSet, filters='__all__'):
    """
    Factory for creating a FilterSet from a model
    """
    # Build up a list of attributes that the Meta object will have.
    attrs = {"model": model, "filters": filters}

    # If parent class already has an inner Meta, the Meta we're
    # creating needs to inherit from the parent's inner meta.
    bases = (base_cls.Meta,) if hasattr(base_cls, "Meta") else ()
    Meta = type("Meta", bases, attrs)

    # Give this new class a reasonable name.
    class_name = model.__name__ + "FilterSet"

    # Class attributes for the new class.
    class_attrs = {"Meta": Meta}

    # Instantiate type() in order to use the same metaclass as the base.
    return type(base_cls)(class_name, (base_cls,), class_attrs)
