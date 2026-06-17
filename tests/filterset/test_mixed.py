from django.db import models

import django_filtering as filtering

from ..market_app.filters import ProductFilterSet
from .utils import get_filter_lookup_mapping


class TestFilterSetCreation:
    """
    Test the construction of a FilterSet class.
    """

    def test_mixed_filters(self):
        """
        Tests the creation of a FilterSet from both imperative and declarative means.
        """

        class User(models.Model):
            name = models.CharField(max_length=120)
            joined_on = models.DateTimeField(auto_now_add=True)
            biography = models.TextField()
            interests = models.CharField(max_length=120)

            class Meta:
                app_label = 'faux_app'

        class UserFilterSet(filtering.FilterSet):
            joined_on = filtering.Filter(
                filtering.PartialDateRangeLookup(),
                label="Joined",
            )

            class Meta:
                model = User
                fields = {
                    "name": ["icontains"],
                    "biography": ["icontains"],
                    "interests": ["icontains"],
                }

        expected_filters = {
            "biography": ["icontains"],
            "interests": ["icontains"],
            "joined_on": ["range"],
            "name": ["icontains"],
        }

        # Expect a mix of imperative and declarative filters
        assert UserFilterSet._meta.filters.keys() == expected_filters.keys()

        # Check for the expected filters and lookups
        filterset = UserFilterSet()
        assert get_filter_lookup_mapping(filterset) == expected_filters

    def test_ordering(self):
        """
        Tests the creation of a FilterSet with ordered filters
        """

        class TestFilterSet(ProductFilterSet):
            class Meta:
                order = (
                    'name',
                    'category',
                    'brand',
                )

        expected_filter_order = [
            'name',
            'category',
            'brand',
            'is_in_stock',
            'quantity',
            'stocked_on',
        ]

        # Expect filter ordered as defined and any remaining to be alphanumerically sorted.
        assert list(TestFilterSet._meta.filters.keys()) == expected_filter_order
