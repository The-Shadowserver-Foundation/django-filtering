from django_filtering.filters import FilterSet

from . import models


class ParticipantFilterSet(FilterSet):
    class Meta:
        model = models.Participant
        filters = '__all__'
