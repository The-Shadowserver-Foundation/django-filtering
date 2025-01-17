import pytest

from model_bakery import baker
from pytest_django import asserts

from django_filtering import filters
from django_filtering.filterset import FilterSet, InvalidFilterSet
from django_filtering.query import Q

from tests.lab_app.models import Participant
from tests.lab_app.filters import ParticipantFilterSet


class TestFilterSetCreation:
    """
    Testing the FilterSet meta class creation.
    """

    @pytest.mark.skip(reason="The `__all__` feature has been disabled")
    def test_derive_all_fields_and_lookups(self):
        """
        Using the ParticipantFilterSet with filters set to '__all__',
        expect all fields and lookups to be valid for use.
        """

        class ScopedFilterSet(FilterSet):
            class Meta:
                model = Participant
                filters = '__all__'

        filterset = ScopedFilterSet()
        field_names = [f.name for f in Participant._meta.get_fields()]
        # Cursor check for all fields
        assert list(filterset.valid_filters.keys()) == field_names

        # Check for all fields and all lookups
        expected_filters = {
            field.name: sorted(list(field.get_lookups().keys()))
            for field in Participant._meta.get_fields()
        }
        assert filterset.valid_filters == expected_filters

    @pytest.mark.skip(reason="Meta option for defining filters disabled")
    def test_derive_scoped_fields_and_lookups(self):
        """
        Using a scoped filterset with filters set in the Meta class,
        expect only those specified fields and lookups to be valid for use.
        """
        valid_filters = {
            "age": ["gte", "lte"],
            "sex": ["exact"],
        }

        class ScopedFilterSet(FilterSet):
            class Meta:
                model = Participant
                filters = valid_filters

        schema = ScopedFilterSet()
        # Check for valid fields and lookups
        assert schema.valid_filters == valid_filters

    def test_explicit_filter_definitions(self):
        """
        Using a filterset with explicitly defined filters,
        expect only those defined filters and lookups to be valid for use.
        """
        valid_filters = {
            "name": ["icontains"],
            "age": ["gte", "lte"],
            "sex": ["exact"],
        }

        class TestFilterSet(FilterSet):
            name = filters.Filter(
                filters.InputLookup('icontains', label='contains'),
                default_lookup="icontains",
                label="Name",
            )
            age = filters.Filter(
                filters.InputLookup('gte', label="greater than or equal to"),
                filters.InputLookup('lte', label="less than or equal to"),
                default_lookup="gte",
                label="Age",
            )
            sex = filters.Filter(
                filters.ChoiceLookup('exact', label='equals'),
                default_lookup='exact',
                label="Sex",
            )

            class Meta:
                model = Participant

        filterset = TestFilterSet()
        assert {f.name: [l.name for l in f.lookups] for f in filterset.filters} == valid_filters


    def test_subclassing_carries_defintions(self):
        """
        Expect subclasses of the FilterSet to carry over the filters defined on the superclass.
        Expect FilterSet set to abstract to not raise when `model` option is missing.
        """
        expected_filters = {
            "name": ["icontains"],
            "age": ["gte", "lte"],
        }

        # Define a base filterset class
        class LabFilterSet(FilterSet):
            name = filters.Filter(
                filters.InputLookup('icontains', label='contains'),
                default_lookup="icontains",
                label="Name",
            )

            class Meta:
                abstract = True

        # Define a class that subclasses the base filterset.
        class ParticipantFilterSet(LabFilterSet):
            age = filters.Filter(
                filters.InputLookup('gte', label="greater than or equal to"),
                filters.InputLookup('lte', label="less than or equal to"),
                default_lookup="gte",
                label="Age",
            )

            class Meta:
                model = Participant

        # Expect resulting classes not to have Meta class attribute
        assert not hasattr(LabFilterSet, 'Meta')
        assert not hasattr(ParticipantFilterSet, 'Meta')

        # Expect subclasses of the FilterSet to carry over the filters defined on the superclass.
        assert [f.name for f in ParticipantFilterSet._meta.filters] == ['name', 'age']

        # Check for the expected filters and lookups
        filterset = ParticipantFilterSet()
        assert {f.name: [l.name for l in f.lookups] for f in filterset.filters} == expected_filters

    def test_metadata_exception_details(self):
        """
        Expect metadata exceptions to provide enough detail to find the problem class.
        """
        with pytest.raises(ValueError) as excinfo:

            class TestMissingFilterSet(FilterSet):
                pass

        assert excinfo.match("TestMissingFilterSet errored")


@pytest.mark.django_db
class TestFilterQuerySet:
    """
    Test the ``FilterSet.filter_queryset`` method results in a filtered queryset.
    """

    def make_participants(self):
        names = ["Aniket Olusola", "Kanta Flora", "Radha Wenilo"]
        # Create objects to filter against
        return list([baker.make(Participant, name=name) for name in names])

    def setup_method(self):
        self.participants = self.make_participants()

    def test_empty_filter_queryset(self):
        filterset = ParticipantFilterSet()
        # Target
        qs = filterset.filter_queryset()
        # Check result is a non-filtered result of either
        # the queryset argument or the base queryset.
        asserts.assertQuerySetEqual(qs, Participant.objects.all())

    def test_filter_queryset(self):
        filter_value = "ni"
        query_data = ['and', [["name", {"lookup": "icontains", "value": filter_value}]]]
        filterset = ParticipantFilterSet(query_data)

        # Target
        qs = filterset.filter_queryset()

        expected_qs = Participant.objects.filter(name__icontains=filter_value).all()
        # Check queryset equality
        asserts.assertQuerySetEqual(qs, expected_qs)

    def test_filter_queryset__with_given_queryset(self):
        filterset = ParticipantFilterSet()
        # Target
        qs = filterset.filter_queryset(Participant.objects.filter(name__icontains="d"))
        # Check queryset equality
        assert list(qs) == [self.participants[-1]]


class TestFilterSetQueryData:
    """
    Test the ``FilterSet.validate`` method by checking the ``is_valid``, ``errors``, and ``query`` properties.
    """

    def test_valid(self):
        """Test valid query data creates a valid query object."""
        data = [
            "and",
            [
                [
                    "name",
                    {"lookup": "icontains", "value": "har"},
                ],
            ],
        ]
        filterset = ParticipantFilterSet(data)
        # Target
        assert filterset.is_valid, filterset.errors
        expected = Q(("name__icontains", "har"), _connector=Q.AND)
        assert filterset.query == expected

    def test_invalid_toplevel_operator(self):
        data = [
            "meh",
            [
                [
                    "name",
                    {"lookup": "icontains", "value": "har"},
                ],
            ],
        ]
        filterset = ParticipantFilterSet(data)
        assert not filterset.is_valid, "should NOT be a valid top-level operator"
        expected_errors = [
            {'json_path': '$[0]', 'message': "'meh' is not one of ['and', 'or']"},
        ]
        assert filterset.errors == expected_errors

    def test_invalid_filter_field(self):
        data = [
            "and",
            [
                [
                    "title",
                    {"lookup": "icontains", "value": "miss"},
                ],
            ],
        ]
        filterset = ParticipantFilterSet(data)
        assert not filterset.is_valid, "should be invalid due to invalid filter name"
        expected_errors = [
            {
                'json_path': '$[1][0]',
                'message': "['title', {'lookup': 'icontains', 'value': 'miss'}] is not valid under any of the given schemas"
            },
        ]
        assert filterset.errors == expected_errors

    def test_invalid_filter_field_lookup(self):
        data = [
            "and",
            [
                [
                    "name",
                    {"lookup": "irandom", "value": "10"},
                ],
            ],
        ]
        filterset = ParticipantFilterSet(data)
        assert not filterset.is_valid, "should be invalid due to invalid filter name"
        expected_errors = [
            {
                'json_path': '$[1][0]',
                'message': "['name', {'lookup': 'irandom', 'value': '10'}] is not valid under any of the given schemas"
            },
        ]
        assert filterset.errors == expected_errors

    def test_invalid_format(self):
        """Check the ``Filterset.filter_queryset`` raises exception when invalid."""
        data = {"and": ["or", ["other", "thing"]]}
        filterset = ParticipantFilterSet(data)

        assert not filterset.is_valid
        expected_errors = [
            {
                'json_path': '$',
                'message': "{'and': ['or', ['other', 'thing']]} is not of type 'array'",
            },
        ]
        assert filterset.errors == expected_errors

    def test_filter_queryset_raises_invalid_exception(self):
        """
        Check the ``Filterset.filter_queryset`` raises exception when invalid.
        The ``FilterSet.is_valid`` property must be checked prior to filtering.
        """
        data = [
            "meh",  # invalid
            [
                [
                    "name",
                    {"lookup": "icontains", "value": "har"},
                ],
            ],
        ]
        filterset = ParticipantFilterSet(data)

        with pytest.raises(InvalidFilterSet):
            filterset.filter_queryset()
