from django_filtering.schema import FilterSchema

from . import models


class ParticipantFilterSchema(FilterSchema):
    class Meta:
        model = models.Participant
        filters = '__all__'
