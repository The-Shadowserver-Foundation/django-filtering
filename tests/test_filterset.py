import pytest

from django.db.models.query_utils import Q
from model_bakery import baker
from pytest_django import asserts

from django_filtering import filters
from django_filtering.filterset import FilterSet, InvalidFilterSet

from tests.lab_app.models import Participant
from tests.lab_app.filters import ParticipantFilterSet
from tests.market_app.filters import (
    KitchenProductFilterSet,
    ProductFilterSet,
    TopBrandKitchenProductFilterSet,
)


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


class TestFilterSetTranslatesQueryData:
    """
    Test the ``FilterSet._make_Q`` method translates the query data to a ``Q`` object.
    """

    def test(self):
        # Simple test case that isn't actually valid query data,
        # because the value of the root array must be a boolean operation
        # (e.g. and, or, not).

        data = (
            "name",
            {"lookup": "icontains", "value": "stove"},
        )
        filterset = ProductFilterSet(data)
        q = filterset._make_Q(filterset.query_data)
        expected = Q(("name__icontains", "stove"), _connector=Q.AND)
        assert q == expected

        data = ("not", ("name", {"lookup": "icontains", "value": "stove"}))
        filterset = ProductFilterSet(data)
        q = filterset._make_Q(filterset.query_data)
        expected = Q(("name__icontains", "stove"), _connector=Q.AND, _negated=True)
        assert q == expected

        data = (
            "not",
            (
                "or",
                (
                    (
                        "name",
                        {"lookup": "icontains", "value": "stove"},
                    ),
                    (
                        "name",
                        {"lookup": "icontains", "value": "oven"},
                    ),
                ),
            ),
        )
        filterset = ProductFilterSet(data)
        q = filterset._make_Q(filterset.query_data)
        expected = ~(Q(name__icontains="stove") | Q(name__icontains="oven"))
        assert q == expected

        data = (
            "or",
            (
                ("name", {"lookup": "icontains", "value": "stove"}),
                (
                    "and",
                    (
                        ("name", {"lookup": "icontains", "value": "oven"}),
                        ("not", ("name", {"lookup": "icontains", "value": "microwave"})),
                    ),
                ),
            ),
        )
        filterset = ProductFilterSet(data)
        q = filterset._make_Q(filterset.query_data)
        expected = Q(name__icontains="stove") | (
            Q(name__icontains="oven") & ~Q(name__icontains="microwave")
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
                                ("name", {"lookup": "icontains", "value": "soap"}),
                                ("name", {"lookup": "icontains", "value": "hand"}),
                                ("not", ("name", {"lookup": "icontains", "value": "lotion"})),
                            ),
                        ),
                        # Note, the missing 'lookup' value, to test default lookup
                        ("brand", {"value": "Safe Soap"}),
                    ),
                ),
            ),
        )
        filterset = ProductFilterSet(data)
        q = filterset._make_Q(filterset.query_data)
        expected = (
            Q(category__in=["Kitchen", "Bath"])
            & Q(stocked__year__gte="2024")
            & (
                (
                    Q(name__icontains="soap")
                    & Q(name__icontains="hand")
                    & ~Q(name__icontains="lotion")
                )
                | Q(brand__exact="Safe Soap")
            )
        )
        assert q == expected

    def test_sticky_filters__without_query_data(self):
        """
        Test when a sticky filter is not present in the user provided query data.
        """
        data = []
        filterset = KitchenProductFilterSet(data)
        assert filterset.is_valid
        q = filterset._query
        # Expect the sticky filter to be added to the query
        expected = Q(("category__exact", "Kitchen"), _connector=Q.AND)
        assert q == expected

    def test_sticky_filters__missing_from_query_data(self):
        """
        Test when a sticky filter is not present in the user provided query data.
        """
        data = [
            "and",
            [
                ["name", {"lookup": "icontains", "value": "sink"}],
            ],
        ]
        filterset = KitchenProductFilterSet(data)
        filterset.validate()
        q = filterset._query
        # Expect the sticky filter to be added to the query
        expected = Q(("category__exact", "Kitchen")) & Q(("name__icontains", "sink"), _connector=Q.AND)
        assert q == expected

    def test_sticky_filter__default_in_query_data(self):
        """
        Test when a sticky filter is present with the default value
        in the user provided query data.
        """
        data = [
            "and",
            [
                ["category", {"lookup": "exact", "value": "Kitchen"}],
                ["name", {"lookup": "icontains", "value": "sink"}],
            ],
        ]
        filterset = KitchenProductFilterSet(data)
        filterset.validate()
        q = filterset._query
        # Expect the sticky filter to be present
        expected = Q(("category__exact", "Kitchen")) & Q(("name__icontains", "sink"), _connector=Q.AND)
        assert q == expected

    def test_sticky_filter__overridden_in_query_data(self):
        """
        Test when a sticky filter is present with a non-default value
        in the user provided query data.
        """
        data = [
            "and",
            [
                ["category", {"lookup": "exact", "value": "Bath"}],
                ["name", {"lookup": "icontains", "value": "sink"}],
            ],
        ]
        filterset = KitchenProductFilterSet(data)
        filterset.validate()
        q = filterset._query
        # Expect the sticky filter to be present
        expected = Q(("category__exact", "Bath")) & Q(("name__icontains", "sink"), _connector=Q.AND)
        assert q == expected

    def test_sticky_filter__unstick_value_in_query_data(self):
        """
        Test when a sticky filter is present with the unstick value
        in the user provided query data.

        This test case essentially tests for the removal
        of the sticky filter from the overall query.
        """
        unstick_user_value = KitchenProductFilterSet._meta.sticky_filters[0].unstick_value
        data = [
            "and",
            [
                ["category", {"lookup": "exact", "value": unstick_user_value}],
                ["name", {"lookup": "icontains", "value": "sink"}],
            ],
        ]
        filterset = KitchenProductFilterSet(data)
        filterset.validate()
        q = filterset._query
        # Expect the sticky filter NOT to be present
        expected = Q(("name__icontains", "sink"), _connector=Q.AND)
        assert q == expected

    def test_several_sticky_filters__without_query_data(self):
        filterset = TopBrandKitchenProductFilterSet()
        assert filterset.is_valid
        q = filterset._query
        # Expect the sticky filter(s) to be present
        expected = Q(
            ('category__exact', 'Kitchen'),
            ('brand__exact', 'MOEN'),
            _connector=Q.AND,
        )
        assert q == expected

    def test_several_sticky_filters__missing_from_query_data(self):
        data = [
            "and",
            [
                ["name", {"lookup": "icontains", "value": "faucet"}],
            ],
        ]
        filterset = TopBrandKitchenProductFilterSet(data)
        filterset.validate()
        q = filterset._query
        # Expect the sticky filter(s) to be present
        expected = Q(
            ('category__exact', 'Kitchen'),
            ('brand__exact', 'MOEN'),
            ("name__icontains", "faucet"),
            _connector=Q.AND,
        )
        assert q == expected

    def test_several_sticky_filters__default_in_query_data(self):
        data = [
            "and",
            [
                ["category", {"lookup": "exact", "value": "Kitchen"}],
                ["name", {"lookup": "icontains", "value": "faucet"}],
            ],
        ]
        filterset = TopBrandKitchenProductFilterSet(data)
        filterset.validate()
        q = filterset._query
        # Expect the sticky filter(s) to be present
        # Note, the order of these might seem wrong,
        # because 'category' was defined before 'brand',
        # but keep in mind the 'category' sticky filter was user provided.
        expected = (
            Q(('brand__exact', 'MOEN'))
            & Q(("category__exact", "Kitchen"))
            & Q(("name__icontains", "faucet"), _connector=Q.AND)
        )
        assert q == expected

    def test_several_sticky_filters__overridden_in_query_data(self):
        data = [
            "and",
            [
                ["category", {"lookup": "exact", "value": "Bath"}],
                ["brand", {"lookup": "exact", "value": "Glacier Bay"}],
                ["name", {"lookup": "icontains", "value": "faucet"}],
            ],
        ]
        filterset = TopBrandKitchenProductFilterSet(data)
        filterset.validate()
        q = filterset._query
        # Expect the sticky filters to be present
        expected = (
            Q(("category__exact", "Bath"))
            & Q(('brand__exact', 'Glacier Bay'))
            & Q(("name__icontains", "faucet"), _connector=Q.AND)
        )
        assert q == expected

    def test_several_sticky_filters__unstick_value_in_query_data(self):
        category_unstick_user_value = TopBrandKitchenProductFilterSet._meta.get_filter('category').unstick_value
        brand_unstick_user_value = TopBrandKitchenProductFilterSet._meta.get_filter('brand').unstick_value
        data = [
            "and",
            [
                ["brand", {"lookup": "exact", "value": brand_unstick_user_value}],
                ["category", {"lookup": "exact", "value": category_unstick_user_value}],
                ["name", {"lookup": "icontains", "value": "faucet"}],
            ],
        ]
        filterset = TopBrandKitchenProductFilterSet(data)
        filterset.validate()
        q = filterset._query
        # Expect the sticky filters NOT to be present
        expected = Q(("name__icontains", "faucet"), _connector=Q.AND)
        assert q == expected


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
