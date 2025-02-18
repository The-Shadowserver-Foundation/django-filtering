from typing import Any, Tuple

from .utils import construct_field_lookup_arg, deconstruct_field_lookup_arg


__all__ = (
    'ChoiceLookup',
    'InputLookup',
    'Filter',
    'StickyFilter',
    'UNSTICK_VALUE',
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


# A sentry value used to signal when a Filter has really been given
# a value that should not be interpretted as queriable.
UNSTICK_VALUE = object()


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
        # Ensure at least one lookup has been defined.
        if len(self.lookups) == 0:
            raise ValueError("Must specify at least one lookup for the filter (e.g. InputLookup).")
        # Assign the default lookup to use or default to the first defined lookup.
        self.default_lookup = default_lookup if default_lookup else self.lookups[0].name
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
            info['help_text'] = field.help_text
        return info

    def to_cleaned_value(self, value):
        """
        Clean the value for database usage.
        """
        return value

    def translate_to_Q_arg(self, value, **kwargs) -> Tuple[str, Any] | None:
        """
        Translates the query data criteria to a Q argument.
        """
        lookup = kwargs.get('lookup', self.default_lookup)
        value = self.to_cleaned_value(value)
        return construct_field_lookup_arg(
            self.name,
            value,
            lookup,
        )


class StickyFilter(Filter):
    """
    A required filter that when present in FilterSet will produce
    a query filter regardless of user input,
    unless the user has specifically overridden the default.

    The filter is present in the FilterSet regardless of the user's input.
    It's not until the user sets this filter explicitly
    to the unstick value--usually a choice--that the filter
    will be removed from the overall query.

    For example, a FilterSet with the model's ``status`` field
    is set to default to ``'Complete```. However we also want to enable the user
    to search for any status. We can achieve this by providing a sticky filter
    that defaults to the desired value, but does not produce a query filter
    when the value results in the unstick value (e.g. empty string or keyword).

        class TaskFilterSet(FilterSet):
            STATUS_CHOICES = [
                ('any', 'Any'),
                ('p', 'Pending'),
                ('c', 'Complete'),
            ]
            status = StickyFilter(
                ChoiceLookup('exact', label='is', choices=STATUS_CHOICES),
                default_value='c',
                unstick_value='any',
                label="Status",
            )
            # ...

    """
    unstick_value = None

    def __init__(self, *args, default_value=None, unstick_value=None, **kwargs):
        super().__init__(*args, **kwargs)
        if default_value is None:
            raise ValueError(
                "A StickyFilter requires a default_value keyword argument value "
                "to correctly function. Please set the value."
            )
        self.default_value = default_value
        self.unstick_value = unstick_value

    def to_cleaned_value(self, value):
        value = super().to_cleaned_value(value)
        if value == self.unstick_value:
            return UNSTICK_VALUE
        return value

    def get_sticky_Q_arg(self) -> Tuple[str, Any]:
        """
        Returns the sticky Q argument
        to be used when the filter is not within the user input.
        """
        return self.translate_to_Q_arg(value=self.default_value)

    def translate_to_Q_arg(self, value, **kwargs) -> Tuple[str, Any] | None:
        """
        Translates the query data criteria to a Q argument.
        """
        lookup = kwargs.get('lookup', self.default_lookup)

        value = self.to_cleaned_value(value)
        if value is UNSTICK_VALUE:
            return None

        return construct_field_lookup_arg(
            self.name,
            value,
            lookup,
        )

    def get_options_schema_info(self, field):
        info = super().get_options_schema_info(field)
        info['is_sticky'] = True
        info['sticky_default'] = deconstruct_field_lookup_arg(*self.get_sticky_Q_arg())
        return info
