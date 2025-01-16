import django_filtering as filtering

from . import models


class ParticipantFilterSet(filtering.FilterSet):
    name = filtering.Filter(
        filtering.InputLookup('icontains', label='contains'),
        default_lookup='icontains',
        label="Name",
    )

    class Meta:
        model = models.Participant
