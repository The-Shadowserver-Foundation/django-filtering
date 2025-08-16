from typing import Any, Tuple

from django.db.models import Q

from .utils import construct_field_lookup_arg, deconstruct_query


__all__ = (
    'ChoiceLookup',
    'InputLookup',
    'Filter',
    'STICKY_SOLVENT_VALUE',
)


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

    The choices will populate from the field's choices.
    Unless explict choices are defined via the ``choices`` argument.
    The ``choices`` argument can be a static list of choices
    or a function that returns a list of choices.

    """
    type = 'choice'

    def __init__(self, *args, choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._choices = choices

    def get_options_schema_definition(self, field):
        definition = super().get_options_schema_definition(field)
        choices = None

        # Use the field's choices or the developer defined choices
        if self._choices is None:
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
        self._transmuter = transmuter or self._default_transmuter
        # Sticky filter properties used to designate the default sticky value
        # and solvent value that removes the sticky value from the resulting query.
        self.sticky_value = sticky_value
        self.solvent_value = solvent_value

    @property
    def is_sticky(self):
        return self.sticky_value is not None

    def get_sticky_Q(self, queryset) -> Q | None:
        """
        Returns a ``Q`` object with the sticky value
        """
        if self.sticky_value is not None:
            return self.transmute(value=self.sticky_value, queryset=queryset)
        return None

    def get_options_schema_info(self, field, queryset):
        lookups = {}
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

    def clean(self, value):
        """
        Clean the value for database usage.
        """
        if value == self.solvent_value:
            return STICKY_SOLVENT_VALUE
        return value

    def _default_transmuter(self, value, queryset, **kwargs) -> Q | None:
        """
        Produces a ``Q`` object from the query data criteria using the known information.
        """
        lookup = kwargs.setdefault('lookup', self.default_lookup)
        return Q(construct_field_lookup_arg(
            self.name,
            value,
            lookup,
        ))

    def transmute(self, value, queryset, **kwargs) -> Q | None:
        """
        Produces a ``Q`` object from the query data criteria.
        """
        value = self.clean(value)
        if value == STICKY_SOLVENT_VALUE:
            # Explicity user selection to remove the sticky filter.
            return None
        kwargs.setdefault('lookup', self.default_lookup)
        return self._transmuter(value, queryset, **kwargs)
