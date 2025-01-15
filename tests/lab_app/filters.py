from django_filtering import filters

from . import models


class ParticipantFilterSet(filters.FilterSet):
    name = filters.Filter(
        filters.InputLookup('icontains', label='contains'),
        default_lookup='icontains',
        label="Name",
    )

    class Meta:
        model = models.Participant
