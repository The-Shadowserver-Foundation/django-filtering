import django.db.models

from django_filtering import filters


class TestInputLookup:
    """
    Testing the InputLookup
    """

    def test(self):
        label = ">="
        field = django.db.models.IntegerField(name='count')

        # Target
        lookup = filters.InputLookup('gte', label=label)

        # Check options schema output
        options_schema_blurb = lookup.get_options_schema_definition(field)
        expected = {'type': 'input', 'label': label}
        assert options_schema_blurb == expected


class TestChoiceLookup:
    """
    Testing the InputLookup
    """

    def test(self):
        label = "is"

        class Type(django.db.models.TextChoices):
            MANUAL = 'manual', 'Manual'
            BULK = 'bulk', 'Bulk'

        field = django.db.models.CharField(name='type', choices=Type.choices, default=Type.MANUAL)

        # Target
        lookup = filters.ChoiceLookup('exact', label=label)

        # Check options schema output
        options_schema_blurb = lookup.get_options_schema_definition(field)
        expected = {
            'type': 'choice',
            'label': label,
            'choices': [('manual', 'Manual'), ('bulk', 'Bulk')],
        }
        assert options_schema_blurb == expected
