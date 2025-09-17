import datetime
from unittest import mock

import pytest
from django.core.exceptions import FieldDoesNotExist
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

    def test_transmute(self):
        lookup_name = 'gte'
        label = ">="
        filter_name = 'count'
        filter = mock.Mock()
        filter.name = filter_name
        lookup = filters.InputLookup(lookup_name, label=label)
        criteria = {'value': 10, 'lookup': lookup_name}

        # Target
        assert lookup.transmute(criteria, context={'filter': filter}) == models.Q(count__gte=10)


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

    def test_transmute(self):
        lookup_name = 'gte'
        label = ">="
        filter_name = 'count'
        filter = mock.Mock()
        filter.name = filter_name
        choices = [(10, 'diez'), (25, 'veinticinco'), (50, 'cincuenta'), (100, 'ciento')]
        lookup = filters.ChoiceLookup(lookup_name, label=label, choices=choices)
        criteria = {'value': 10, 'lookup': lookup_name}

        # Target
        assert lookup.transmute(criteria, context={'filter': filter}) == models.Q(count__gte=10)


class TestDateRangeLookup:
    """
    Testing the InputLookup
    """

    def test(self):
        lookup_name = 'rangez'
        label = "between"
        field = models.DateField()
        filter = mock.Mock()
        filter.name = 'created'
        d1, d2 = [datetime.date(2025, 1, 1), datetime.date(2025, 8, 31)]

        # Target
        lookup = filters.DateRangeLookup(lookup_name, label=label)

        # Check options schema output
        options_schema_blurb = lookup.get_options_schema_definition(field)
        expected = {'type': 'date-range', 'label': label}
        assert options_schema_blurb == expected

        # Check the cleaning of the values in the filter criteria
        dirty_criteria = {'value': [d1.isoformat(), d2.isoformat()], 'lookup': lookup_name}
        cleaned_criteria = {'value': [d1.isoformat(), d2.isoformat()], 'lookup': lookup_name}
        assert lookup.clean(dirty_criteria) == cleaned_criteria

        # Check the transmutation of the criteria to Q instance.
        expected = models.Q(**{
            f'{filter.name}__gte': d1.isoformat(),
            f'{filter.name}__lte': d2.isoformat(),
        })
        assert lookup.transmute(cleaned_criteria, context={'filter': filter}) == expected

    @pytest.mark.skip(reason="not yet implemented")
    def test_validation(self):
        # Check the validation of jsonschema 'date' format
        # Note, `format` validation requires explicit configuration in jsonschema.
        pass


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
        filter_field_name = 'page_count'
        field = models.IntegerField()
        label = "Pages"
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

        # Mock the bound (i.e. `Filter.bind`) instance of the filter.
        filterset = mock.MagicMock()
        model = mock.MagicMock()
        filterset._meta.model = model
        model._meta.get_field.return_value = field
        filter = filter.bind(filter_field_name)

        # Check options schema output
        context = {'filterset': filterset, 'filter': filter, 'queryset': None}
        options_schema_info = filter.get_options_schema_info(context)
        expected = {
            'default_lookup': default_lookup,
            'label': label,
            'lookups': {
                a[0]: {'label': kw['label'], 'type': cls.type}
                for cls, a, kw in lookups_data
            },
        }
        assert options_schema_info == expected

    def test_get_options_schema_info__for_non_field_filter(self):
        filter_name = 'is_published'
        label = "Is published"
        default_lookup = 'exact'
        lookups_data = (
            [
                filters.ChoiceLookup,
                (default_lookup,),
                {'label': ':', 'choices': [('no', 'No'), ('yes', 'Yes')]},
            ],
        )


        # Target
        filter = filters.Filter(
            *[cls(*a, **kw) for cls, a, kw in lookups_data],
            default_lookup=default_lookup,
            label=label,
        )

        # Mock the bound (i.e. `Filter.bind`) instance of the filter.
        filterset = mock.MagicMock()
        filterset._meta.model._meta.get_field.side_effect = FieldDoesNotExist()
        filter = filter.bind(filter_name)

        # Check options schema output
        context = {'filterset': filterset, 'filter': filter, 'queryset': None}
        options_schema_info = filter.get_options_schema_info(context)
        expected = {
            'default_lookup': default_lookup,
            'label': label,
            'lookups': {
                default_lookup: {
                    'label': lookups_data[0][2]['label'],
                    'type': 'choice',
                    'choices': lookups_data[0][2]['choices'],
                }
            },
        }
        assert options_schema_info == expected

    def test_transmute(self):
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
        filter = filter.bind(name='pages')

        # Check translation of _query data's criteria_ to django Q argument
        criteria = {'lookup': 'gte', 'value': '50'}
        context = {
            'filterset': None,  # not needed for this test
            'filter': filter,
            'queryset': None,  # not needed for this test
        }
        assert filter.transmute(criteria, context=context) == models.Q(pages__gte='50')

    def test_valid_json_types(self):
        # TODO Expand this test to cover native json types: number, null, array, and object.

        def assertion_transmuter(criteria, **kwargs):
            from django.db.models import Q

            assert isinstance(criteria['value'], bool)
            return Q(something__in=['a', 'b', 'c'])

        filter = filters.Filter(
            filters.ChoiceLookup('exact', label=":", choices=((True, 'Yes'), (False, 'No'))),
            label='Has something?',
            transmuter=assertion_transmuter,
        )
        criteria = {'lookup': 'exact', 'value': True}
        context = {
            'filterset': None,  # not needed for this test
            'filter': filter,
            'queryset': None,  # not needed for this test
        }
        assert filter.transmute(criteria, context=context)


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
        solvent_value = 'any'
        sticky_value = 'manual'

        # Create the filter
        filter = filters.Filter(
            filters.ChoiceLookup('exact', label='is', choices=choices),
            label=label,
            solvent_value=solvent_value,
            sticky_value=sticky_value,
        )
        # Manually set the Filter's name attribute,
        # which is otherwise handled by the FilterSet metaclass.
        filter = filter.bind(name='type')

        # Check translation of query data's criteria to django Q argument
        criteria = {'lookup': 'exact', 'value': 'bulk'}
        context = {
            'filterset': None,  # not needed for this test
            'filter': filter,
            'queryset': None,  # not needed for this test
        }
        assert filter.transmute(criteria, context=context) == models.Q(type__exact='bulk')

        # Ensure value does not translate to a Q argument
        criteria = {'lookup': 'exact', 'value': solvent_value}
        context = {
            'filterset': None,  # not needed for this test
            'filter': filter,
            'queryset': None,  # not needed for this test
        }
        assert filter.transmute(criteria, context=context) == None

        # Check the default Q argument
        assert filter.get_sticky_Q(context=context) == models.Q(type__exact=sticky_value)
