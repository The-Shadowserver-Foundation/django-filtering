from django_filtering.schema import FilterSchema


class TestFilterSchema:
    def test_derive_all_fields_and_lookups(self):
        # Using the ParticipantFilterSchema with filters set to '__all__',
        # expect all fields and lookups to be valid for use.
        from tests.lab_app.filters import ParticipantFilterSchema
        from tests.lab_app.models import Participant

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
        # Using the ParticipantScopedFilterSchema with filters set in the Meta class,
        # expect only those specified fields and lookups to be valid for use.
        from tests.lab_app.models import Participant

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
