import pytest

from django.db import models

from django_filtering import filters
from django_filtering.filterset import (
    ALL_FIELDS,
    filters_for_model,
    FilterSet,
)

from tests.lab_app.models import Participant

from .utils import get_filter_lookup_mapping


class TestFiltersForModel:
    """Tests the ``filters_for_model`` function."""

    def test_no_fields(self):

        class Thing(models.Model):
            name = models.CharField(max_length=20)

            class Meta:
                app_label = 'faux_app'

        filters_map = filters_for_model(Thing, fields=None)
        assert filters_map == {}

    def test_all_fields(self):
        """
        Test for the creation of filters for all fields on a model.
        """

        class Post(models.Model):
            content = models.CharField(max_length=120)
            created_at = models.DateTimeField(auto_now_add=True)

            class Meta:
                app_label = 'faux_app'

        # Target
        filters_map = filters_for_model(Post, fields=ALL_FIELDS)

        # Check for the following filters
        expected = {
            'content': filters.Filter(
                filters.InputLookup("exact"),
                filters.InputLookup("iexact"),
                filters.InputLookup("gt"),
                filters.InputLookup("gte"),
                filters.InputLookup("lt"),
                filters.InputLookup("lte"),
                filters.InputLookup("in"),
                filters.InputLookup("contains"),
                filters.InputLookup("icontains"),
                filters.InputLookup("startswith"),
                filters.InputLookup("istartswith"),
                filters.InputLookup("endswith"),
                filters.InputLookup("iendswith"),
                filters.InputLookup("range"),
                filters.InputLookup("isnull"),
                filters.InputLookup("regex"),
                filters.InputLookup("iregex"),
                label="Content",
            ).bind('content'),
            'created_at': filters.Filter(
                filters.InputLookup("exact"),
                filters.InputLookup("iexact"),
                filters.InputLookup("gt"),
                filters.InputLookup("gte"),
                filters.InputLookup("lt"),
                filters.InputLookup("lte"),
                filters.InputLookup("in"),
                filters.InputLookup("contains"),
                filters.InputLookup("icontains"),
                filters.InputLookup("startswith"),
                filters.InputLookup("istartswith"),
                filters.InputLookup("endswith"),
                filters.InputLookup("iendswith"),
                filters.InputLookup("range"),
                filters.InputLookup("isnull"),
                filters.InputLookup("regex"),
                filters.InputLookup("iregex"),
                filters.InputLookup("year"),
                filters.InputLookup("month"),
                filters.InputLookup("day"),
                filters.InputLookup("week_day"),
                filters.InputLookup("iso_week_day"),
                filters.InputLookup("week"),
                filters.InputLookup("iso_year"),
                filters.InputLookup("quarter"),
                filters.InputLookup("hour"),
                filters.InputLookup("minute"),
                filters.InputLookup("second"),
                filters.InputLookup("date"),
                filters.InputLookup("time"),
                label="Created at"
            ).bind('created_at'),
            'id': filters.Filter(
                filters.InputLookup("exact"),
                filters.InputLookup("iexact"),
                filters.InputLookup("gt"),
                filters.InputLookup("gte"),
                filters.InputLookup("lt"),
                filters.InputLookup("lte"),
                filters.InputLookup("in"),
                filters.InputLookup("contains"),
                filters.InputLookup("icontains"),
                filters.InputLookup("startswith"),
                filters.InputLookup("istartswith"),
                filters.InputLookup("endswith"),
                filters.InputLookup("iendswith"),
                filters.InputLookup("range"),
                filters.InputLookup("isnull"),
                filters.InputLookup("regex"),
                filters.InputLookup("iregex"),
                label="ID",
            ).bind('id'),
        }
        assert sorted(filters_map.keys()) == sorted(expected.keys())
        for name, filter in filters_map.items():
            assert filter == expected[name]

    def test_all_fields__with_many_to_many_fields(self):

        # Example models come from the Django ManyToMany field documentation
        # https://docs.djangoproject.com/en/5.2/ref/models/fields/#manytomanyfield

        class Manufacturer(models.Model):
            name = models.CharField(max_length=255)
            clients = models.ManyToManyField(
                "self", symmetrical=False, related_name="suppliers", through="Supply"
            )

            class Meta:
                app_label = 'faux_app'

        class Supply(models.Model):
            supplier = models.ForeignKey(
                Manufacturer, models.CASCADE, related_name="supplies_given"
            )
            client = models.ForeignKey(
                Manufacturer, models.CASCADE, related_name="supplies_received"
            )
            product = models.CharField(max_length=255)

            class Meta:
                app_label = 'faux_app'

        # Target
        filters_map = filters_for_model(Manufacturer, fields=ALL_FIELDS)

        # Check for the following filters
        generally_expected_lookups = (
            filters.InputLookup("exact"),
            filters.InputLookup("iexact"),
            filters.InputLookup("gt"),
            filters.InputLookup("gte"),
            filters.InputLookup("lt"),
            filters.InputLookup("lte"),
            filters.InputLookup("in"),
            filters.InputLookup("contains"),
            filters.InputLookup("icontains"),
            filters.InputLookup("startswith"),
            filters.InputLookup("istartswith"),
            filters.InputLookup("endswith"),
            filters.InputLookup("iendswith"),
            filters.InputLookup("range"),
            filters.InputLookup("isnull"),
            filters.InputLookup("regex"),
            filters.InputLookup("iregex"),
        )
        relationally_expected_lookups = (
            filters.InputLookup("in"),
            filters.InputLookup("exact"),
            filters.InputLookup("lt"),
            filters.InputLookup("gt"),
            filters.InputLookup("gte"),
            filters.InputLookup("lte"),
            filters.InputLookup("isnull"),
        )
        expected = {
            'id': filters.Filter(
                *generally_expected_lookups,
                label="ID",
            ).bind('id'),
            'name': filters.Filter(
                *generally_expected_lookups,
                label="Name",
            ).bind('name'),
            'clients': filters.Filter(
                *generally_expected_lookups,
                label="Manufacturer",
            ).bind('clients'),
            'suppliers': filters.Filter(
                *generally_expected_lookups,
                label="Manufacturer",
            ).bind('suppliers'),
            'supplies_given': filters.Filter(
                *relationally_expected_lookups,
                label="Supply",
            ).bind('supplies_given'),
            'supplies_received': filters.Filter(
                *relationally_expected_lookups,
                label="Supply",
            ).bind('supplies_received'),
        }
        assert sorted(filters_map.keys()) == sorted(expected.keys())
        for name, filter in filters_map.items():
            assert filter == expected[name]


class TestDeclarativeFilterSetCreation:
    """
    Test the construction of a FilterSet class.
    """

    def test_derive_all_fields_and_lookups(self):
        """
        Define a FilterSet with fields metadata set to '__all__'.
        Expect all fields and lookups to be valid for use.
        """

        class AllFields(models.Model):
            name = models.CharField(max_length=20)

            class Meta:
                app_label = 'faux_app'

        class AllFieldsFilterSet(FilterSet):
            class Meta:
                model = AllFields
                fields = ALL_FIELDS

        filterset = AllFieldsFilterSet()
        field_names = [f.name for f in AllFields._meta.get_fields()]
        # Cursor check for all fields
        assert sorted([f.name for f in filterset.filters]) == sorted(field_names)

        # Check for all fields and all lookups
        expected_filters = {
            field.name: list(field.get_lookups().keys())
            for field in AllFields._meta.get_fields()
        }
        assert get_filter_lookup_mapping(filterset) == expected_filters

    def test_derive_some_fields_and_lookups(self):
        """
        Define a FilterSet with some fields and lookups declared through metadata.
        Expect only those specified fields and lookups to be valid for use.
        """
        expected_filters = {
            "age": ["gte", "lte"],
            "sex": ["exact"],
        }

        class TestFilterSet(FilterSet):
            class Meta:
                model = Participant
                fields = expected_filters

        filterset = TestFilterSet()

        # Cursor check for all fields
        field_names = list(expected_filters.keys())
        assert sorted([f.name for f in filterset.filters]) == sorted(field_names)

        # Check for all fields and all lookups
        assert get_filter_lookup_mapping(filterset) == expected_filters
