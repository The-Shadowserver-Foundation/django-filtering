import django_filtering as filtering

from . import models


class ProductFilterSet(filtering.FilterSet):
    name = filtering.Filter(
        filtering.InputLookup('icontains', label='contains'),
        label="Name",
    )
    category = filtering.Filter(
        filtering.ChoiceLookup('in', label="in"),
        label="Category",
    )
    stocked = filtering.Filter(
        filtering.InputLookup(['year', 'gte'], label="year >="),
        label="Stocked",
    )
    brand = filtering.Filter(
        filtering.InputLookup('exact', label="is"),
        label="Brand",
    )

    class Meta:
        model = models.Product
