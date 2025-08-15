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
        default_lookup='exact',
        label="Continent",
        transmuter=utils.continent_to_countries,
    )

    class Meta:
        model = models.Study
