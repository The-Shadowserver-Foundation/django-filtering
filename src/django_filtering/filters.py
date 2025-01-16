__all__ = (
    'ChoiceLookup',
    'InputLookup',
    'Filter',
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
