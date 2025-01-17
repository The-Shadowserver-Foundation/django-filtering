import warnings

import jsonschema
from django.conf import settings
from django.db.models import QuerySet

from .filters import Filter
from .query import Q
from .schema import JSONSchema, FilteringOptionsSchema
from .utils import merge_dicts


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
        '_inherited_filters',
        '_defined_filters',
    )
    KEYWORD_ARGS = PUBLIC_KEYWORD_ARGS + PRIVATE_KEYWORD_ARGS

    def __init__(self, **kwargs):
        self.is_abstract = kwargs.get('abstract', False)
        self.model = kwargs.get("model", None)
        if self.model is None and not self.is_abstract:
            raise RequiredMetadataError("`model` is required.")

        if kwargs.get("filters", None):
            warnings.warn(
                (
                    "The FilterSet.Meta.filters property has been "
                    "temporarily disabled. Instead, please subclass FilterSet "
                    "and assign Filter attributes."
                ),
                UserWarning,
            )

        self._filters = kwargs.get('_inherited_filters', []) + kwargs.get('_defined_filters', [])

    def get_inheritable_options(self) -> dict:
        """
        Provides options that can be inherited by a subclass.
        """
        return {
            'model': self.model,
            '_inherited_filters': self._filters,
        }

    @property
    def filters(self):
        return self._filters


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

        # Pull out filters from the class definition
        filters = []
        cls_attrs = {}
        for a, v in attrs.items():
            if not isinstance(v, Filter):
                cls_attrs[a] = v
                continue
            v.name = a
            filters.append(v)
        # Prepare definitions in meta options
        meta_opts['_defined_filters'] = filters

        # Declare meta class options for runtime usage
        opts = merge_dicts(*[
            cls._meta.get_inheritable_options()
            for cls in bases if isinstance(cls, FilterSetType)
        ], meta_opts)
        try:
            cls_attrs['_meta'] = Metadata(**opts)
        except MetadataException as exc:
            if isinstance(exc, RequiredMetadataError):
                raise ValueError(
                    f"Creation of {name} errored due "
                    f"to a missing required metadata property: {exc.args[0]}"
                )

        # Create the new class
        return super().__new__(mcs, name, bases, cls_attrs)


class InvalidQueryData(Exception):
    pass


class InvalidFilterSet(Exception):
    pass


class FilterSet(metaclass=FilterSetType):

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

    @property
    def filters(self):
        return self._meta.filters

    def get_queryset(self):
        return self._meta.model.objects.all()

    def filter_queryset(self, queryset=None) -> QuerySet:
        if not self.is_valid:
            raise InvalidFilterSet(
                "The query is invalid! "
                "Hint, check `is_valid` before running `filter_queryset`.\n"
                f"Errors:\n{self._errors}"
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

        # Bail out when the query_data is empty or undefined
        if not self.query_data:
            return

        # Validates both the schema and the data
        validator = self._make_json_schema_validator(self.json_schema.schema)
        for err in validator.iter_errors(self.query_data):
            # TODO We can provide better detail than simply echoing
            #      the exception details. See jsonschema.exceptions.best_match.
            self._errors.append({
                'json_path': err.json_path,
                'message': err.message,
            })

        # Translate to Q objects
        if not self._errors:
            self._query = Q.from_query_data(self.query_data)


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
