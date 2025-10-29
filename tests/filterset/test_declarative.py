import pytest

from django.db import models

from django_filtering import filters
from django_filtering.filterset import (
    ALL_FIELDS,
    filters_for_model,
)


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
                filters.InputLookup("exact", label="exact"),
                filters.InputLookup("iexact", label="iexact"),
                filters.InputLookup("gt", label="gt"),
                filters.InputLookup("gte", label="gte"),
                filters.InputLookup("lt", label="lt"),
                filters.InputLookup("lte", label="lte"),
                filters.InputLookup("in", label="in"),
                filters.InputLookup("contains", label="contains"),
                filters.InputLookup("icontains", label="icontains"),
                filters.InputLookup("startswith", label="startswith"),
                filters.InputLookup("istartswith", label="istartswith"),
                filters.InputLookup("endswith", label="endswith"),
                filters.InputLookup("iendswith", label="iendswith"),
                filters.InputLookup("range", label="range"),
                filters.InputLookup("isnull", label="isnull"),
                filters.InputLookup("regex", label="regex"),
                filters.InputLookup("iregex", label="iregex"),
                label="Content",
            ),
            'created_at': filters.Filter(
                filters.InputLookup("exact", label="exact"),
                filters.InputLookup("iexact", label="iexact"),
                filters.InputLookup("gt", label="gt"),
                filters.InputLookup("gte", label="gte"),
                filters.InputLookup("lt", label="lt"),
                filters.InputLookup("lte", label="lte"),
                filters.InputLookup("in", label="in"),
                filters.InputLookup("contains", label="contains"),
                filters.InputLookup("icontains", label="icontains"),
                filters.InputLookup("startswith", label="startswith"),
                filters.InputLookup("istartswith", label="istartswith"),
                filters.InputLookup("endswith", label="endswith"),
                filters.InputLookup("iendswith", label="iendswith"),
                filters.InputLookup("range", label="range"),
                filters.InputLookup("isnull", label="isnull"),
                filters.InputLookup("regex", label="regex"),
                filters.InputLookup("iregex", label="iregex"),
                filters.InputLookup("year", label="year"),
                filters.InputLookup("month", label="month"),
                filters.InputLookup("day", label="day"),
                filters.InputLookup("week_day", label="week_day"),
                filters.InputLookup("iso_week_day", label="iso_week_day"),
                filters.InputLookup("week", label="week"),
                filters.InputLookup("iso_year", label="iso_year"),
                filters.InputLookup("quarter", label="quarter"),
                filters.InputLookup("hour", label="hour"),
                filters.InputLookup("minute", label="minute"),
                filters.InputLookup("second", label="second"),
                filters.InputLookup("date", label="date"),
                filters.InputLookup("time", label="time"),
                label="Created at"
            ),
            'id': filters.Filter(
                filters.InputLookup("exact", label="exact"),
                filters.InputLookup("iexact", label="iexact"),
                filters.InputLookup("gt", label="gt"),
                filters.InputLookup("gte", label="gte"),
                filters.InputLookup("lt", label="lt"),
                filters.InputLookup("lte", label="lte"),
                filters.InputLookup("in", label="in"),
                filters.InputLookup("contains", label="contains"),
                filters.InputLookup("icontains", label="icontains"),
                filters.InputLookup("startswith", label="startswith"),
                filters.InputLookup("istartswith", label="istartswith"),
                filters.InputLookup("endswith", label="endswith"),
                filters.InputLookup("iendswith", label="iendswith"),
                filters.InputLookup("range", label="range"),
                filters.InputLookup("isnull", label="isnull"),
                filters.InputLookup("regex", label="regex"),
                filters.InputLookup("iregex", label="iregex"),
                label="ID",
            ),
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
            filters.InputLookup("exact", label="exact"),
            filters.InputLookup("iexact", label="iexact"),
            filters.InputLookup("gt", label="gt"),
            filters.InputLookup("gte", label="gte"),
            filters.InputLookup("lt", label="lt"),
            filters.InputLookup("lte", label="lte"),
            filters.InputLookup("in", label="in"),
            filters.InputLookup("contains", label="contains"),
            filters.InputLookup("icontains", label="icontains"),
            filters.InputLookup("startswith", label="startswith"),
            filters.InputLookup("istartswith", label="istartswith"),
            filters.InputLookup("endswith", label="endswith"),
            filters.InputLookup("iendswith", label="iendswith"),
            filters.InputLookup("range", label="range"),
            filters.InputLookup("isnull", label="isnull"),
            filters.InputLookup("regex", label="regex"),
            filters.InputLookup("iregex", label="iregex"),
        )
        relationally_expected_lookups = (
            filters.InputLookup("in", label="in"),
            filters.InputLookup("exact", label="exact"),
            filters.InputLookup("lt", label="lt"),
            filters.InputLookup("gt", label="gt"),
            filters.InputLookup("gte", label="gte"),
            filters.InputLookup("lte", label="lte"),
            filters.InputLookup("isnull", label="isnull"),
        )
        expected = {
            'id': filters.Filter(
                *generally_expected_lookups,
                label="ID",
            ),
            'name': filters.Filter(
                *generally_expected_lookups,
                label="Name",
            ),
            'clients': filters.Filter(
                *generally_expected_lookups,
                label="Manufacturer",
            ),
            'suppliers': filters.Filter(
                *generally_expected_lookups,
                label="Manufacturer",
            ),
            'supplies_given': filters.Filter(
                *relationally_expected_lookups,
                label="Supply",
            ),
            'supplies_received': filters.Filter(
                *relationally_expected_lookups,
                label="Supply",
            ),
        }
        assert sorted(filters_map.keys()) == sorted(expected.keys())
        for name, filter in filters_map.items():
            assert filter == expected[name]
