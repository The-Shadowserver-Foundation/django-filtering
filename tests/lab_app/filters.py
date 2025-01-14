from django_filtering import filters

from . import models


class ParticipantFilterSet(filters.FilterSet):
    name = filters.Filter(filters.InputLookup('icontains', label='contains'))

    class Meta:
        model = models.Participant
