import jsonschema
from django.conf import settings
from django.db.models import QuerySet

from .query import Q
from .schema import JSONSchema, FilteringOptionsSchema


class BaseLookup:
    """
    Represents a model field database lookup.
    The ``name`` is a valid field lookup (e.g. `icontains`, `exact`).
    The ``label`` is the human readable name for the lookup.
    This may be used by the frontend implemenation to display
    the lookup's relationship to a field.
    """
    type = 'input'

    def __init__(self, name, label=None):
        self.name = name
        if label is None:
            raise ValueError("At this time, the lookup label must be provided.")
        self.label = label

    def get_options_schema_definition(self, field):
        """Returns a dict for use by the options schema."""
        return {
            "type": self.type,
            "label": self.label,
        }


class InputLookup(BaseLookup):
    """
    Represents an text input type field lookup.
    """


class ChoiceLookup(BaseLookup):
    """
    Represents a choice selection input type field lookup.
    """
    type = 'choice'

    def get_options_schema_definition(self, field):
        definition = super().get_options_schema_definition(field)
        definition['choices'] = list(field.get_choices(include_blank=False))
        return definition


class Filter:
    """
    The model field to filter on using the given ``lookups``.
    The ``default_lookup`` is intended to be used by the frontend
    to auto-select the lookup relationship.
    The ``label`` is the human readable name of the field.

    The ``name`` attribute is assigned by the FilterSet's metaclass.
    """
    name = None

    def __init__(self, *lookups, default_lookup=None, label=None):
        self.lookups = lookups
        if default_lookup is None:
            raise ValueError("At this time, the default_lookup must be provided.")
        self.default_lookup = default_lookup
        if label is None:
            raise ValueError("At this time, the filter label must be provided.")
        self.label = label

    def get_options_schema_info(self, field):
        lookups = {}
        for lu in self.lookups:
            lookups[lu.name] = lu.get_options_schema_definition(field)
        info = {
            "default_lookup": self.default_lookup,
            "lookups": lookups,
            "label": self.label
        }
        if hasattr(field, "help_text") and field.help_text:
            info['description'] = field.help_text
        return info


class RequiredOption(Exception):
    """
    Raised when a Meta class option is undefined and required.
    """


class Options:
    """
    FilterSet Meta class Options.
    This class is used to instantiate ``FilterSet._meta``.
    """

    def __init__(self, base_filters=None, options=None):
        self.model = getattr(options, "model", None)
        if self.model is None:
            raise RequiredOption("Option `model` is Required.")
        self._filters = base_filters if base_filters else []

    @property
    def filters(self):
        return self._filters


class FilterSetMetaclass(type):
    def __new__(mcs, name, bases, attrs):
        super_new = super().__new__
        # Capture the meta configuration
        meta_attrs = attrs.pop('Meta', {})

        # Pull out filters from the class definition
        filters = []
        cls_attrs = {}
        for a, v in attrs.items():
            if not isinstance(v, Filter):
                cls_attrs[a] = v
                continue
            v.name = a
            filters.append(v)

        # Return the base class without additional alterations
        if bases == (BaseFilterSet,):
            return super_new(mcs, name, bases, cls_attrs)

        # Declare meta class options for runtime usage
        cls_attrs['_meta'] = Options(filters, meta_attrs)

        # Create the new class
        return super_new(mcs, name, bases, cls_attrs)


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


class FilterSet(BaseFilterSet, metaclass=FilterSetMetaclass):
    pass


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
