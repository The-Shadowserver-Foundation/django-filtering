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


class KitchenProductFilterSet(filtering.FilterSet):
    name = filtering.Filter(
        filtering.InputLookup('icontains', label="contains"),
        label="Name",
    )
    category = filtering.StickyFilter(
        filtering.ChoiceLookup('exact', label="equals"),
        unstick_value='',
        default_value="Kitchen",
        label="Category",
    )
    class Meta:
        model = models.Product


class TopBrandKitchenProductFilterSet(KitchenProductFilterSet):
    BRAND_CHOICES = [
        ('all', 'All brands'),
        ('Delta', 'Delta'),
        ('MOEN', 'MOEN'),
        ('Glacier Bay', 'Glacier Bay'),
    ]
    brand = filtering.StickyFilter(
        filtering.ChoiceLookup('exact', label='is', choices=BRAND_CHOICES),
        default_value="MOEN",
        unstick_value='all',
        label="Brand",
    )
