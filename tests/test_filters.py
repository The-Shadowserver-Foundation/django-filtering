import pytest
from django.db import models

from django_filtering import filters


class TestInputLookup:
    """
    Testing the InputLookup
    """

    def test(self):
        label = ">="
        field = models.IntegerField(name='count')

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

        class Type(models.TextChoices):
            MANUAL = 'manual', 'Manual'
            BULK = 'bulk', 'Bulk'

        field = models.CharField(name='type', choices=Type.choices, default=Type.MANUAL)

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

        class Type(models.TextChoices):
            MANUAL = 'manual', 'Manual'
            BULK = 'bulk', 'Bulk'

        target_field = models.CharField(name='type', choices=Type.choices, default=Type.MANUAL)
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

        class Type(models.TextChoices):
            MANUAL = 'manual', 'Manual'
            BULK = 'bulk', 'Bulk'

        target_field = models.CharField(name='type', choices=Type.choices, default=Type.MANUAL)
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


class TestFilter:
    """
    Test Filter behavior
    """

    def test_init_wo_label(self):
        with pytest.raises(ValueError) as exc_info:
            filters.Filter(filters.InputLookup('icontains', label='contains'), default_lookup='icontains')
        assert exc_info.type is ValueError
        assert exc_info.value.args[0] == "At this time, the filter label must be provided."

    def test_init_wo_default_lookup(self):
        # Target
        filter = filters.Filter(
            filters.InputLookup('exact', label='matches'),
            filters.InputLookup('icontains', label='contains'),
            label='name',
        )

        # Expect first lookup to be the default
        assert filter.default_lookup == 'exact'

    def test_init_w_default_lookup(self):
        # Target
        filter = filters.Filter(
            filters.InputLookup('exact', label='exactly matches'),
            filters.InputLookup('iexact', label='case insensitively matches'),
            filters.InputLookup('icontains', label='contains'),
            default_lookup='iexact',
            label='name',
        )

        # Expect first lookup to be the default
        assert filter.default_lookup == 'iexact'

    def test_get_options_schema_info(self):
        label = "Pages"
        field = models.IntegerField(name='pages')
        lookups_data = (
            [filters.InputLookup, ('gte',), {'label': '>='}],
            [filters.InputLookup, ('lte',), {'label': '<='}],
            [filters.InputLookup, ('exact',), {'label': '='}],
        )
        default_lookup = 'exact'

        # Target
        filter = filters.Filter(
            *[cls(*a, **kw) for cls, a, kw in lookups_data],
            default_lookup=default_lookup,
            label=label,
        )

        # Check options schema output
        options_schema_info = filter.get_options_schema_info(field)
        expected = {
            'default_lookup': default_lookup,
            'label': label,
            'lookups': {
                a[0]: {'label': kw['label'], 'type': cls.type}
                for cls, a, kw in lookups_data
            },
        }
        assert options_schema_info == expected

    def test_translate_to_Q_arg(self):
        label = "Pages"
        choices = [
            ('10', '10'),
            ('50', '50'),
            ('100', '100'),
            ('200', '200'),
        ]
        lookups_data = (
            [filters.InputLookup, ('exact',), {'label': '='}],
            [filters.ChoiceLookup, ('gte',), {'label': '>=', 'choices': choices}],
            [filters.ChoiceLookup, ('lte',), {'label': '<=', 'choices': choices}],
        )

        # Create the filter
        filter = filters.Filter(
            *[cls(*a, **kw) for cls, a, kw in lookups_data],
            label=label,
        )
        filter.name = 'pages'

        # Check translation of _query data's criteria_ to django Q argument
        criteria = {'lookup': 'gte', 'value': '50'}
        assert filter.translate_to_Q_arg(**criteria) == ('pages__gte', '50')


class TestStickyFilter:

    def test(self):
        """
        This test case assumes usage in a FilterSet
        with a model that has a 'type' field,
        where the filter defaults to the 'Manual' choice.
        """
        label = "Type"
        choices = [
            ('any', 'Any'),
            ('manual', 'Manual'),
            ('bulk', 'Bulk'),
        ]
        unstick_value = 'any'
        default_value = 'manual'

        # Create the filter
        filter = filters.StickyFilter(
            filters.ChoiceLookup('exact', label='is', choices=choices),
            label=label,
            unstick_value=unstick_value,
            default_value=default_value,
        )
        # Manually set the Filter's name attribute,
        # which is otherwise handled by the FilterSet metaclass.
        filter.name = 'type'

        # Check translation of query data's criteria to django Q argument
        criteria = {'lookup': 'exact', 'value': 'bulk'}
        assert filter.translate_to_Q_arg(**criteria) == ('type__exact', 'bulk')

        # Ensure value does not translate to a Q argument
        criteria = {'lookup': 'exact', 'value': unstick_value}
        assert filter.translate_to_Q_arg(**criteria) == None

        # Check the default Q argument
        assert filter.get_sticky_Q_arg() == ('type__exact', default_value)
