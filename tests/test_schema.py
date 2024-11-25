import pytest
from django_filtering.schema import FilterSchema
from model_bakery import baker

from tests.lab_app.models import Participant
from tests.lab_app.filters import ParticipantFilterSchema


class TestFilterSchema:
    def test_derive_all_fields_and_lookups(self):
        """
        Using the ParticipantFilterSchema with filters set to '__all__',
        expect all fields and lookups to be valid for use.
        """
        schema = ParticipantFilterSchema()
        field_names = [f.name for f in Participant._meta.get_fields()]
        # Cursor check for all fields
        assert list(schema.valid_filters.keys()) == field_names

        # Check for all fields and all lookups
        expected_filters = {
            field.name: {lookup_name for lookup_name in field.get_lookups().keys()}
            for field in Participant._meta.get_fields()
        }
        assert schema.valid_filters == expected_filters

    def test_derive_scoped_fields_and_lookups(self):
        """
        Using the ParticipantScopedFilterSchema with filters set in the Meta class,
        expect only those specified fields and lookups to be valid for use.
        """
        valid_filters = {
            "age": {"gte", "lte"},
            "sex": {"exact"},
        }

        class ScopedFilterSchema(FilterSchema):
            class Meta:
                model = Participant
                filters = valid_filters

        schema = ScopedFilterSchema()
        # Check for valid fields and lookups
        assert schema.valid_filters == valid_filters

    @pytest.mark.django_db
    def test_filter_queryset(self):
        """
        Test the FilterSchema.filter_queryset method results in a filtered queryset.
        """

        # Create objects to filter against
        baker.make(Participant, name="Aniket Olusola")
        baker.make(Participant, name="Kanta Flora")
        third_participant = baker.make(Participant, name="Radha Wenilo")

        filter_value = "ni"
        query_data = ['and', [["name", {"lookup": "icontains", "value": filter_value}]]]
        schema = ParticipantFilterSchema(query_data)

        # Target (1 of 2)
        qs = schema.filter_queryset()

        expected_qs = Participant.objects.filter(name__icontains=filter_value).all()
        # Check queryset equality
        assert list(qs) == list(expected_qs)

        # Target (2 of 2)
        qs = schema.filter_queryset(Participant.objects.filter(name__icontains="d"))
        # Check queryset equality
        assert list(qs) == [third_participant]
