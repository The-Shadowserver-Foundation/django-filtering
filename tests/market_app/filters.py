import django_filtering as filtering

from . import models


def query_in_stock(value, queryset, **kwargs):
    from django.db.models import Q

    if value is True:
        return Q(quantity__gt=0)
    else:
        return Q(quantity__lt=0)

class ProductFilterSet(filtering.FilterSet):
    name = filtering.Filter(
        filtering.InputLookup('icontains', label='contains'),
        label="Name",
    )
    category = filtering.Filter(
        filtering.ChoiceLookup('in', label="in"),
        label="Category",
    )
    stocked_on = filtering.Filter(
        filtering.InputLookup(['year', 'gte'], label="year >="),
        label="Stocked",
    )
    quantity = filtering.Filter(
        filtering.InputLookup(['gte'], label=">="),
        label="Quantity",
    )
    brand = filtering.Filter(
        filtering.InputLookup('exact', label="is"),
        label="Brand",
    )

    is_in_stock = filtering.Filter(
        filtering.ChoiceLookup('exact', label=":", choices=[(True, "Yes"), (False, "No")]),
        label="Is in stock?",
        transmuter=query_in_stock,
    )

    class Meta:
        model = models.Product


class KitchenProductFilterSet(filtering.FilterSet):
    name = filtering.Filter(
        filtering.InputLookup('icontains', label="contains"),
        label="Name",
    )
    category = filtering.Filter(
        filtering.ChoiceLookup('exact', label="equals"),
        solvent_value='',
        sticky_value="Kitchen",
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
    brand = filtering.Filter(
        filtering.ChoiceLookup('exact', label='is', choices=BRAND_CHOICES),
        sticky_value="MOEN",
        solvent_value='all',
        label="Brand",
    )
