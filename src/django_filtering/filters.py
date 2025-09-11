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

    def __init__(self, name, label):
        self.name = name
        if label is None:
            raise ValueError("At this time, the lookup label must be provided.")
        self.label = label

    def get_options_schema_definition(self, field=None):
        """Returns a dict for use by the options schema."""
        return {
            "type": self.type,
            "label": self.label,
        }

    def clean(self, value: Any):
        return value

    def transmute(self, filterset=None, filter=None, queryset=None, criteria=None, **kwargs) -> Q | None:
        raise NotImplementedError()


class SingleFieldLookup(Lookup):
    """
    Lookup for a single field on a model.
    The ``name`` parameter is a valid field lookup (e.g. `icontains`, `exact`).
    """

    def transmute(self, **kwargs) -> Q | None:
        """
        Produces a ``Q`` object from the query data criteria using the known information.
        """
        filter = kwargs['filter']
        criteria = kwargs['criteria']
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


# A sentry value used to signal when the user has selected
# to remove the sticky filter.
STICKY_SOLVENT_VALUE = object()


class Filter:
    """
    The model field to filter on using the given ``lookups``.
    The ``default_lookup`` is intended to be used by the frontend
    to auto-select the lookup relationship.
    The ``label`` is the human readable name of the field.

    The ``name`` attribute is assigned by the FilterSet's metaclass.
    """
    name = None
    filterset = None

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

    def bind(self, name: str, filterset: 'FilterSet') -> 'Filter':
        """
        Returns a copy of this filter,
        with assignments from the given ``name`` and ``filterset`` instance.
        """
        filter = deepcopy(self)
        filter.name = name
        filter.filterset = filterset
        filter.model = filterset._meta.model
        return filter

    @property
    def is_sticky(self):
        return self.sticky_value is not None

    def get_sticky_Q(self, queryset) -> Q | None:
        """
        Returns a ``Q`` object with the sticky value
        """
        if self.sticky_value is not None:
            context = {
                'filterset': self.filterset,
                'filter': self,
                'queryset': queryset,
                'criteria': {'value': self.sticky_value},
            }
            return self.transmute(**context)
        return None

    def get_options_schema_info(self, queryset):
        lookups = {}
        try:
            field = self.model._meta.get_field(self.name)
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
            info['sticky_default'] = deconstruct_query(self.get_sticky_Q(queryset))
        return info

    def clean(self, criteria):
        """
        Clean the value for database usage.
        """
        result = criteria.copy()
        value = criteria['value']
        if value == self.solvent_value:
            result['value'] = STICKY_SOLVENT_VALUE
        return result

    def transmute(self, criteria, **kwargs) -> Q | None:
        """
        Produces a ``Q`` object from the query data criteria.
        """
        criteria = self.clean(criteria)
        if criteria['value'] == STICKY_SOLVENT_VALUE:
            # Explicity user selection to remove the sticky filter.
            return None
        criteria.setdefault('lookup', self.default_lookup)
        if self._transmuter:
            return self._transmuter(criteria=criteria, **kwargs)
        else:
            lookup = [lu for lu in self.lookups if lu.name == criteria['lookup']][0]
            return lookup.transmute(criteria=criteria, **kwargs)
