import pytest
from django_filtering.filters import FilterSet, InvalidFilterSet, InvalidQueryData, Q
from model_bakery import baker
from pytest_django import asserts

from tests.lab_app.models import Participant
from tests.lab_app.filters import ParticipantFilterSet


class TestQ:
    def test_from_query_data(self):
        data = (
            "title",
            {"lookup": "icontains", "value": "stove"},
        )
        q = Q.from_query_data(data)
        expected = Q(("title__icontains", "stove"), _connector=Q.AND)
        assert q == expected

        data = ("not", ("title", {"lookup": "icontains", "value": "stove"}))
        q = Q.from_query_data(data)
        expected = Q(("title__icontains", "stove"), _connector=Q.AND, _negated=True)
        assert q == expected

        data = (
            "not",
            (
                "or",
                (
                    (
                        "title",
                        {"lookup": "icontains", "value": "stove"},
                    ),
                    (
                        "title",
                        {"lookup": "icontains", "value": "oven"},
                    ),
                ),
            ),
        )
        q = Q.from_query_data(data)
        expected = ~(Q(title__icontains="stove") | Q(title__icontains="oven"))
        assert q == expected

        data = (
            "or",
            (
                ("title", {"lookup": "icontains", "value": "stove"}),
                (
                    "and",
                    (
                        ("title", {"lookup": "icontains", "value": "oven"}),
                        ("not", ("title", {"lookup": "icontains", "value": "microwave"})),
                    ),
                ),
            ),
        )
        q = Q.from_query_data(data)
        expected = Q(title__icontains="stove") | (
            Q(title__icontains="oven") & ~Q(title__icontains="microwave")
        )
        assert q == expected

        data = (
            "and",
            (
                ("category", {"lookup": "in", "value": ["Kitchen", "Bath"]}),
                ("stocked", {"lookup": ["year", "gte"], "value": "2024"}),
                (
                    "or",
                    (
                        (
                            "and",
                            (
                                ("title", {"lookup": "icontains", "value": "soap"}),
                                ("title", {"lookup": "icontains", "value": "hand"}),
                                ("not", ("title", {"lookup": "icontains", "value": "lotion"})),
                            ),
                        ),
                        # Note, the missing 'lookup' value, to test default lookup
                        ("brand", {"value": "Safe Soap"}),
                    ),
                ),
            ),
        )
        q = Q.from_query_data(data)
        expected = (
            Q(category__in=["Kitchen", "Bath"])
            & Q(stocked__year__gte="2024")
            & (
                (
                    Q(title__icontains="soap")
                    & Q(title__icontains="hand")
                    & ~Q(title__icontains="lotion")
                )
                | Q(brand__iexact="Safe Soap")
            )
        )
        assert q == expected

    def test_to_query_data(self):
        q = Q(("title__icontains", "stove"), _connector=Q.AND)
        data = q.to_query_data()
        expected = (
            "title",
            {"lookup": "icontains", "value": "stove"},
        )
        assert data == expected

        q = Q(("title__icontains", "stove"), _connector=Q.AND, _negated=True)
        data = q.to_query_data()
        expected = ("not", ("title", {"lookup": "icontains", "value": "stove"}))
        assert data == expected

        q = ~(Q(title__icontains="stove") | Q(title__icontains="oven"))
        data = q.to_query_data()
        expected = (
            "not",
            (
                "or",
                (
                    (
                        "title",
                        {"lookup": "icontains", "value": "stove"},
                    ),
                    (
                        "title",
                        {"lookup": "icontains", "value": "oven"},
                    ),
                ),
            ),
        )
        assert data == expected

        q = Q(title__icontains="stove") | (
            Q(title__icontains="oven") & ~Q(title__icontains="microwave")
        )
        data = q.to_query_data()
        expected = (
            "or",
            (
                ("title", {"lookup": "icontains", "value": "stove"}),
                (
                    "and",
                    (
                        ("title", {"lookup": "icontains", "value": "oven"}),
                        ("not", ("title", {"lookup": "icontains", "value": "microwave"})),
                    ),
                ),
            ),
        )
        assert data == expected

        q = (
            Q(category__in=["Kitchen", "Bath"])
            & Q(stocked__year__gte="2024")
            & (
                (
                    Q(title__icontains="soap")
                    & Q(title__icontains="hand")
                    & ~Q(title__icontains="lotion")
                )
                | Q(brand__iexact="Safe Soap")
            )
        )
        data = Q.to_query_data(q)
        expected = (
            "and",
            (
                ("category", {"lookup": "in", "value": ["Kitchen", "Bath"]}),
                ("stocked", {"lookup": ["year", "gte"], "value": "2024"}),
                (
                    "or",
                    (
                        (
                            "and",
                            (
                                ("title", {"lookup": "icontains", "value": "soap"}),
                                ("title", {"lookup": "icontains", "value": "hand"}),
                                ("not", ("title", {"lookup": "icontains", "value": "lotion"})),
                            ),
                        ),
                        ("brand", {"lookup": "iexact", "value": "Safe Soap"}),
                    ),
                ),
            ),
        )
        assert data == expected


class TestFilterSet:
    def test_derive_all_fields_and_lookups(self):
        """
        Using the ParticipantFilterSet with filters set to '__all__',
        expect all fields and lookups to be valid for use.
        """
        schema = ParticipantFilterSet()
        field_names = [f.name for f in Participant._meta.get_fields()]
        # Cursor check for all fields
        assert list(schema.valid_filters.keys()) == field_names

        # Check for all fields and all lookups
        expected_filters = {
            field.name: sorted(list(field.get_lookups().keys()))
            for field in Participant._meta.get_fields()
        }
        assert schema.valid_filters == expected_filters

    def test_derive_scoped_fields_and_lookups(self):
        """
        Using the ParticipantScopedFilterSet with filters set in the Meta class,
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
