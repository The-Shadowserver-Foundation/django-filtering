from django.db.models import Q

import django_filtering as filtering

from . import models
from . import utils


class ParticipantFilterSet(filtering.FilterSet):
    name = filtering.Filter(
        filtering.InputLookup('icontains', label='contains'),
        default_lookup='icontains',
        label="Name",
    )

    class Meta:
        model = models.Participant


class StudyFilterSet(filtering.FilterSet):
    name = filtering.Filter(
        filtering.InputLookup('icontains', label='contains'),
        default_lookup='icontains',
        label="Name",
    )
    continent = filtering.Filter(
        filtering.ChoiceLookup(
            "exact",
            label="is",
            choices=utils.CONTINENT_CHOICES,
        ),
        label="Continent",
    )

    def transmute_continent(self, criteria, context):
        country_codes = utils.continent_to_countries(criteria['value'])
        return Q(country__in=country_codes)

    class Meta:
        model = models.Study
