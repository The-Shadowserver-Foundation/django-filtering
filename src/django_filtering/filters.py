from copy import deepcopy
from typing import Any

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q

from .utils import construct_field_lookup_arg, deconstruct_query


__all__ = (
    'ChoiceLookup',
    'DateRangeLookup',
    'InputLookup',
    'Filter',
    'STICKY_SOLVENT_VALUE',
)


class Lookup:
    """
    Represents a model field database lookup.
    The ``name`` is a valid field lookup (e.g. `icontains`, `exact`).
    The ``label`` is the human readable name for the lookup.
    This may be used by the frontend implemenation to display
    the lookup's relationship to a field.
    """
    type = None

    def __init__(self, name: str, label: str):
        self.name = name
        self.label = label

    def get_options_schema_definition(self, field=None):
        """Returns a dict for use by the options schema."""
        return {
            "type": self.type,
            "label": self.label,
        }

    def __repr__(self):
        return f'<{self.__class__.__name__} name="{self.name}" type="{self.type}" label="{self.label}">'

    def clean(self, value: Any):
        return value

    def transmute(self, criteria: dict[str, Any], context: dict[str, Any]) -> Q | None:
        raise NotImplementedError()


class SingleFieldLookup(Lookup):
    """
    Lookup for a single field on a model.
    The ``name`` parameter is a valid field lookup (e.g. `icontains`, `exact`).
    """

    def transmute(self, criteria: dict[str, Any], context: dict[str, Any]) -> Q | None:
        """
        Produces a ``Q`` object from the query data criteria using the known information.
        """
        filter = context['filter']
        return Q(construct_field_lookup_arg(
            filter.name,
            criteria['value'],
            criteria['lookup'],
        ))


class InputLookup(SingleFieldLookup):
    """
    Represents an text input type field lookup.
    """
    type = 'input'


class ChoiceLookup(SingleFieldLookup):
    """
    Represents a choice selection input type field lookup.

    The choices will populate from the field's choices.
    Unless explict choices are defined via the ``choices`` argument.
    The ``choices`` argument can be a static list of choices
    or a function that returns a list of choices.

    """
    type = 'choice'

    def __init__(self, *args, choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._choices = choices

    def get_options_schema_definition(self, field=None):
        definition = super().get_options_schema_definition(field)
        choices = None

        # Use the field's choices or the developer defined choices
        if self._choices is None:
            if field is None:
                raise RuntimeError(
                    f"No choices were defined for '{self.name}' "
                    "and we could not discover choices "
                    f"because '{self.name}' is not a field on the model."
                )
            else:
                choices = list(field.get_choices(include_blank=False))
        else:
            if callable(self._choices):
                choices = self._choices(lookup=self, field=field)
            else:
                choices = self._choices

        definition['choices'] = choices
        return definition


class DateRangeLookup(Lookup):
    """
    Represents inputs for querying between a date range.

    """
    type = 'date-range'

    # At this time there is no reason to _clean_ the value
    # and turn it into a `datetime.date`.
    # The database is capable of casting a string to its native date type
    # as long we enforce iso 8601 formatting.

    def transmute(self, criteria: dict[str, Any], context: dict[str, Any]) -> Q | None:
        filter = context['filter']
        return Q(
            construct_field_lookup_arg(
                filter.name,
                criteria['value'][0],
                'gte',
            ),
            construct_field_lookup_arg(
                filter.name,
                criteria['value'][1],
                'lte',
            )
        )


# A sentry value used to signal when the user has selected
# to remove the sticky filter.
STICKY_SOLVENT_VALUE = object()


class Filter:
    """
    The model field to filter on using the given ``lookups``.
    The ``default_lookup`` is intended to be used by the frontend
    to auto-select the lookup relationship.
    The ``label`` is the human readable name of the field.

    The ``_name`` attribute is assigned by the FilterSet's metaclass
    through the ``bind`` method.

    """
    _name = None

    def __init__(
        self,
        *lookups,
        default_lookup=None,
        label=None,
        transmuter=None,
        sticky_value=None,
        solvent_value=None,
    ):
        self.lookups = lookups
        # Ensure at least one lookup has been defined.
        if len(self.lookups) == 0:
            raise ValueError("Must specify at least one lookup for the filter (e.g. InputLookup).")
        # Assign the default lookup to use or default to the first defined lookup.
        self.default_lookup = default_lookup if default_lookup else self.lookups[0].name
        if label is None:
            raise ValueError("At this time, the filter label must be provided.")
        self.label = label
        self._transmuter = transmuter
        # Sticky filter properties used to designate the default sticky value
        # and solvent value that removes the sticky value from the resulting query.
        self.sticky_value = sticky_value
        self.solvent_value = solvent_value

    def __repr__(self):
        sup_repr = super().__repr__()
        repr_parts = sup_repr.split('object')
        return ' '.join(
            [
                repr_parts[0],
                f'name="{self.name}"',
                f'label="{self.label}"',
            ] + repr_parts[1:],
        )

    @property
    def name(self):
        return self._name

    def bind(self, name: str) -> 'Filter':
        """
        Returns a copy of this filter with assignments from the given ``name``,
        which is the name given to the Filter in the FilterSet.
        """
        filter = deepcopy(self)
        filter._name = name
        return filter

    @property
    def is_sticky(self):
        return self.sticky_value is not None

    def get_sticky_Q(self, context: dict[str, Any]) -> Q | None:
        """
        Returns a ``Q`` object with the sticky value
        """
        if self.sticky_value is not None:
            return self.transmute({'value': self.sticky_value}, context=context)
        return None

    def get_options_schema_info(self, context: dict[str, Any]):
        lookups = {}
        model = context['filterset']._meta.model
        try:
            field = model._meta.get_field(self.name)
        except FieldDoesNotExist:
            field = None

        for lu in self.lookups:
            lookups[lu.name] = lu.get_options_schema_definition(field)
        info = {
            "default_lookup": self.default_lookup,
            "lookups": lookups,
            "label": self.label
        }
        if hasattr(field, "help_text") and field.help_text:
            info['help_text'] = field.help_text
        if self.is_sticky:
            info['is_sticky'] = True
            info['sticky_default'] = deconstruct_query(self.get_sticky_Q(context))
        return info

    def get_lookup(self, name=None) -> Lookup:
        if name is None:
            name = self.default_lookup
        return [lu for lu in self.lookups if lu.name == name][0]

    def clean(self, criteria) -> dict[str, Any]:
        """
        Clean the criteria for database usage.
        """
        # Make a copy of the criteria that we will mutate.
        cleaned = criteria.copy()

        # Defer to the lookup instance for cleaning specifics
        cleaned['value'] = self.get_lookup(criteria.get('lookup')).clean(criteria['value'])

        # Check if the cleaned value is the solvent that removes the sticky filter.
        if cleaned['value'] == self.solvent_value:
            cleaned['value'] = STICKY_SOLVENT_VALUE
        return cleaned

    def transmute(self, criteria: dict[str, Any], context: dict[str, Any]) -> Q | None:
        """
        Produces a ``Q`` object from the query data criteria.
        """
        criteria = self.clean(criteria)
        if criteria['value'] == STICKY_SOLVENT_VALUE:
            # Explicity user selection to remove the sticky filter.
            return None

        # Set the lookup name for the transmuter's convenience.
        lookup_name = criteria.setdefault('lookup', self.default_lookup)

        if self._transmuter:
            transmuter = self._transmuter
        else:
            transmuter = self.get_lookup(lookup_name).transmute
        return transmuter(criteria, context=context)
