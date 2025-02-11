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

    def test_static_choices(self):
        label = "is"

        class Type(django.db.models.TextChoices):
            MANUAL = 'manual', 'Manual'
            BULK = 'bulk', 'Bulk'

        target_field = django.db.models.CharField(name='type', choices=Type.choices, default=Type.MANUAL)
        static_choices = [
            ('any', 'Any'),
            ('manual', 'Manual'),
            ('bulk', 'Bulk'),
        ]

        # Target
        lookup = filters.ChoiceLookup('exact', label=label, choices=static_choices)

        # Check options schema output
        options_schema_blurb = lookup.get_options_schema_definition(target_field)
        expected = {
            'type': 'choice',
            'label': label,
            'choices': static_choices,
        }
        assert options_schema_blurb == expected

    def test_dynamic_choices(self):
        label = "is"

        class Type(django.db.models.TextChoices):
            MANUAL = 'manual', 'Manual'
            BULK = 'bulk', 'Bulk'

        target_field = django.db.models.CharField(name='type', choices=Type.choices, default=Type.MANUAL)
        static_choices = [
            ('any', 'Any'),
            ('manual', 'Manual'),
            ('bulk', 'Bulk'),
        ]

        def dynamic_choices(lookup, field):
            assert isinstance(lookup, filters.ChoiceLookup)
            assert field == target_field
            return static_choices

        # Target
        lookup = filters.ChoiceLookup('exact', label=label, choices=dynamic_choices)

        # Check options schema output
        options_schema_blurb = lookup.get_options_schema_definition(target_field)
        expected = {
            'type': 'choice',
            'label': label,
            'choices': static_choices,
        }
        assert options_schema_blurb == expected
