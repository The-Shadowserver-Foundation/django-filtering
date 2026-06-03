from copy import deepcopy

import pytest
from django import forms
from django.utils.datastructures import MultiValueDict

from django_filtering.conf import settings
from django_filtering.filters import (
    ChoiceLookup,
    DateRangeLookup,
    Filter,
    InputLookup,
    YesNoChoiceLookup,
)
from django_filtering.filterset import FilterSet
from django_filtering.forms import FlatFilteringForm, flat_filtering_form_factory
from django_filtering.forms.fields import DateRangeField
from tests.lab_app.filters import ParticipantFilterSet, StudyFilterSet
from tests.lab_app.models import Participant, Study
from tests.market_app.filters import ProductFilterSet, TopBrandKitchenProductFilterSet


class TestLookupToFormField:
    def test_InputLookup(self):
        lookup = InputLookup("iexact", label="is")
        filter = Filter(lookup, label="Name")
        filter = filter.bind("name")

        filterset = None  # Unused in this test
        form_fields = filter.as_form_fields(filterset)
        assert len(form_fields) == 1
        assert isinstance(form_fields[f"{filter.name}__{lookup.name}"], forms.CharField)

    def test_ChoiceLookup__from_choices_argument(self):
        choices = [("y", "Yes"), ("n", "No")]
        lookup = ChoiceLookup("exact", choices=choices)
        filter = Filter(lookup, label="Category")
        filter = filter.bind("category")

        filterset = None  # Unused in this test
        form_fields = filter.as_form_fields(filterset)
        assert len(form_fields) == 1
        form_field = form_fields[f"{filter.name}__{lookup.name}"]
        assert isinstance(form_field, forms.ChoiceField)
        assert form_field.choices == settings.BLANK_CHOICE + choices

    def test_ChoiceLookup__from_field_choices(self):
        class TestFilterSet(StudyFilterSet):
            state = Filter(ChoiceLookup("exact"), label="State")

        model = TestFilterSet._meta.model
        filter = TestFilterSet._meta.filters['state']
        lookup = filter.lookups[0]

        form_fields = filter.as_form_fields(TestFilterSet)
        assert len(form_fields) == 1
        form_field = form_fields[f"{filter.name}__{lookup.name}"]
        # Expect an instance of ChoiceField
        assert isinstance(form_field, forms.ChoiceField)
        assert form_field.choices == model._meta.get_field('state').get_choices()

    def test_ChoiceLookup__from_related_field_choices(self):
        class TestFilterSet(StudyFilterSet):
            participants = Filter(ChoiceLookup("exact"), label="Participant")

        filter = TestFilterSet._meta.filters['participants']
        lookup = filter.lookups[0]

        form_fields = filter.as_form_fields(TestFilterSet)
        assert len(form_fields) == 1
        form_field = form_fields[f"{filter.name}__{lookup.name}"]
        # Expect an instance of ModelChoiceField with queryset for choices.
        assert isinstance(form_field, forms.ModelChoiceField)
        assert form_field.empty_label == settings.BLANK_CHOICE[0][1]
        # No need to test for the queryset, because ModelChoiceField
        # init is strict with this requirement.

    def test_ChoiceLookup__from_reverse_related_field_choices(self):
        class TestFilterSet(ParticipantFilterSet):
            studies = Filter(ChoiceLookup("exact"), label="Study")

        filter = TestFilterSet._meta.filters['studies']
        lookup = filter.lookups[0]

        form_fields = filter.as_form_fields(TestFilterSet)
        assert len(form_fields) == 1
        form_field = form_fields[f"{filter.name}__{lookup.name}"]
        # Expect an instance of ModelChoiceField with queryset for choices.
        assert isinstance(form_field, forms.ModelChoiceField)
        # Test the queryset is using the correct model
        assert form_field.queryset.model is Study

    def test_ChoiceLookup__for_sticky_filter(self):
        filter = TopBrandKitchenProductFilterSet._meta.filters['brand']
        lookup = filter.lookups[0]
        assert isinstance(lookup, ChoiceLookup)  # to verify it wasn't accidentally changed.

        form_fields = filter.as_form_fields(TopBrandKitchenProductFilterSet)
        assert len(form_fields) == 1
        form_field = form_fields[f"{filter.name}__{lookup.name}"]
        # Expect an instance of ChoiceField
        assert isinstance(form_field, forms.ChoiceField)
        # Expect there not to be a blank choice, because this is a sticky filter
        assert form_field.choices == TopBrandKitchenProductFilterSet.BRAND_CHOICES

    def test_DateRangeLookup(self):
        lookup = DateRangeLookup(label="between")
        filter = Filter(lookup, label="Created")
        filter = filter.bind("created")

        filterset = None  # Unused in this test
        form_fields = filter.as_form_fields(filterset)
        assert len(form_fields) == 1
        assert isinstance(form_fields[f'{filter.name}__{lookup.name}'], DateRangeField)


class TestFilterSetFormAdaptation:
    def make_em(self, FilterSet, **kwargs):
        return FilterSet, flat_filtering_form_factory(FilterSet, **kwargs)

    def test_call_with_invalid_bases(self):
        with pytest.raises(TypeError) as caught_exc:
            FilterSet, Form = self.make_em(StudyFilterSet, bases=())
        assert (
            caught_exc.value.args[0] == "One of the given base classes must be FlatFilteringForm or a subclass of it."
        )

    def test_call_with_base_class(self):
        _, Form = self.make_em(StudyFilterSet, bases=FlatFilteringForm)
        assert issubclass(Form, FlatFilteringForm)

    def test_blank(self):
        FilterSet, Form = self.make_em(StudyFilterSet)

        # Expect the Form to be constructed with fields from the FilterSet.
        expected_form_fields = {
            'continent__exact': forms.ChoiceField,
            'name__icontains': forms.CharField,
        }
        for field_name, field_cls in expected_form_fields.items():
            assert field_name in Form.base_fields
            assert isinstance(Form.base_fields[field_name], field_cls)

        # Expect the Form's class name to derive from the FilterSet class name.
        assert Form.__name__ == f"{FilterSet.__name__}Form"

    def test_blank__with_sticky_filters(self):
        FilterSet, Form = self.make_em(TopBrandKitchenProductFilterSet)

        expected_form_fields = {
            'brand__exact': forms.ChoiceField,
            'category__exact': forms.ChoiceField,
            'name__icontains': forms.CharField,
        }
        for field_name, field_cls in expected_form_fields.items():
            assert field_name in Form.base_fields
            assert isinstance(Form.base_fields[field_name], field_cls)

        # Expect the form to be aware of the sticky fields.
        assert Form.Meta.sticky_fields == ['brand__exact', 'category__exact']

        # Expect the form to have initial values set to the sticky values.
        filterset = FilterSet()
        form = Form(filterset)
        expected = {
            'brand__exact': FilterSet._meta.filters['brand'].sticky_value,
            'category__exact': FilterSet._meta.filters['category'].sticky_value,
        }
        assert form.initial == expected

    def test_init_initial_from_filterset(self):
        """
        Testing form init sets the ``initial`` data from the filterset.
        """
        FilterSet, Form = self.make_em(StudyFilterSet)

        f1_value = 'body temp'
        f2_value = 'SA'
        query_data = [
            'and',
            [
                ['name', {'lookup': 'icontains', 'value': f1_value}],
                ['continent', {'lookup': 'exact', 'value': f2_value}],
            ],
        ]
        filterset = FilterSet(query_data)
        form = Form(filterset)

        # Expect the initial values to be set from the filterset's query data.
        expected_initial = {
            'name__icontains': f1_value,
            'continent__exact': f2_value,
        }
        assert form.initial == expected_initial
        assert form.is_enabled

    def test_init_initial_from_filterset__with_sticky_filters(self):
        """
        Testing form init sets the ``initial`` data from the filterset.
        """
        FilterSet, Form = self.make_em(TopBrandKitchenProductFilterSet)

        f1_value = 'temp'
        f2_value = 'all'
        query_data = [
            'and',
            [
                ['name', {'lookup': 'icontains', 'value': f1_value}],
                # sticky `brand` is in here
                ['category', {'lookup': 'exact', 'value': f2_value}],
            ],
        ]
        filterset = FilterSet(query_data)
        form = Form(filterset)

        # Expect the initial values to be set from the filterset's query data.
        expected_initial = {
            'name__icontains': f1_value,
            'category__exact': f2_value,
            'brand__exact': filterset.get_filter('brand').sticky_value,
        }
        assert form.initial == expected_initial
        assert form.is_enabled

    def test_disables_fields_for_multivalue(self):
        """
        Testing form fields are disabled
        when the filterset's query data has multiple values per filter lookup.
        """
        FilterSet, Form = self.make_em(StudyFilterSet)

        f1_value = 'temp'
        f2_value = 'cryogen'
        query_data = [
            'and',
            [
                ['name', {'lookup': 'icontains', 'value': f1_value}],
                ['name', {'lookup': 'icontains', 'value': f2_value}],
            ],
        ]
        filterset = FilterSet(query_data)
        form = Form(filterset)

        # Expect the initial data to have removed the initial value for the field,
        # because otherwise the target field would have multiple values assigned to it.
        expected_initial = {}
        assert form.initial == expected_initial
        assert form.is_enabled

        # Expect the field to be disabled,
        # because it has multiple values assigned to it.
        assert form.fields['name__icontains'].disabled

    def test_disables_fields_for_multivalue__with_sticky_filters(self):
        """
        Testing form fields are disabled
        when the filterset's query data has multiple values per filter lookup.
        """
        FilterSet, Form = self.make_em(TopBrandKitchenProductFilterSet)

        f1_value = 'Kitchen'
        f2_value = 'Bath'
        query_data = [
            'and',
            [
                ['category', {'lookup': 'exact', 'value': f1_value}],
                ['category', {'lookup': 'exact', 'value': f2_value}],
            ],
        ]
        filterset = FilterSet(query_data)
        form = Form(filterset)

        # Expect the initial data to contain an empty value,
        # because otherwise the target field would have multiple values assigned to it.
        expected_initial = {
            'brand__exact': filterset.get_filter('brand').sticky_value,
        }
        assert form.initial == expected_initial
        assert form.is_enabled

        # Expect the field to be disabled,
        # because it has multiple values assigned to it.
        assert form.fields['category__exact'].disabled

    def test_form_adds_to_filterset(self):
        """
        Testing the form's submission with data adds to the filterset's query data.
        """
        FilterSet, Form = self.make_em(StudyFilterSet)

        f1_value = 'temp'
        f2_value = 'SA'
        query_data = [
            'and',
            [
                ['name', {'lookup': 'icontains', 'value': f1_value}],
            ],
        ]
        data = {
            'name__icontains': f1_value,
            'continent__exact': f2_value,  # added
        }
        filterset = FilterSet(deepcopy(query_data))
        form = Form(filterset, data)

        # Invoke cleaning; and thus translation of form data to query data.
        assert not form.errors

        # Expect a condition to have been added to the query data.
        expected_query_data = deepcopy(query_data)
        expected_query_data[1].append(['continent', {'lookup': 'exact', 'value': f2_value}])
        assert filterset.query_data == expected_query_data

    def test_form_updates_filterset(self):
        """
        Testing the form's submission with data updates the filterset's query data.
        """
        FilterSet, Form = self.make_em(StudyFilterSet)

        f1_value = 'temp'
        f2_value = 'cryogen'
        query_data = [
            'and',
            [
                ['name', {'lookup': 'icontains', 'value': f1_value}],
            ],
        ]
        data = {
            'name__icontains': f2_value,  # updated
        }
        filterset = FilterSet(deepcopy(query_data))
        form = Form(filterset, data)

        # Invoke cleaning; and thus translation of form data to query data.
        assert not form.errors

        # Expect the condition's value to have changed.
        expected_query_data = deepcopy(query_data)
        expected_query_data[1][0] = ['name', {'lookup': 'icontains', 'value': f2_value}]
        assert filterset.query_data == expected_query_data

    def test_form_removes_from_filterset(self):
        """
        Testing the form's submission with data removes from the filterset's query data.
        """
        FilterSet, Form = self.make_em(StudyFilterSet)

        f1_value = 'temp'
        query_data = [
            'and',
            [
                ['name', {'lookup': 'icontains', 'value': f1_value}],
            ],
        ]
        data = {}
        filterset = FilterSet(deepcopy(query_data))
        form = Form(filterset, data)

        # Invoke cleaning; and thus translation of form data to query data.
        assert not form.errors

        # Expect the condition to have been dropped
        # and the form to have cleared the query data.
        expected_query_data = []
        assert filterset.query_data == expected_query_data

    def test_form_removes_from_filterset__with_sticky_filters(self):
        """
        Testing the form's submission with data removes from the filterset's query data.
        """
        FilterSet, Form = self.make_em(TopBrandKitchenProductFilterSet)

        f1_value = 'all'
        query_data = [
            'and',
            [
                ['category', {'lookup': 'exact', 'value': f1_value}],
            ],
        ]
        data = {
            'category': 'Kitchen',  # reset to sticky value
            'brand__exact': 'MOEN',  # was already set to sticky value
        }
        filterset = FilterSet(deepcopy(query_data))
        form = Form(filterset, data)

        # Invoke cleaning; and thus translation of form data to query data.
        assert not form.errors

        # Expect the condition to have been dropped
        # and the form to have cleared the query data.
        expected_query_data = []
        assert filterset.query_data == expected_query_data

    def try_using_disabled_form(self, form):
        # Invoke validation; assuming enabled was ignored.
        assert form.errors

        # Expect the Form to have errors.
        expected_error_message = ["The form is disabled when nested filters or non-'and' operations are used."]
        assert form.errors['__all__'] == expected_error_message

    def assert_form_is_disabled(self, form):
        # Expect the form to know it is not enabled.
        assert form.is_enabled is False

        # Expect the initial values to be unset.
        assert form.initial == {}

        # Expect all form fields to be disabled
        assert all(f.disabled for f in form.fields.values())

    def test_form_disabled__with_other_operators(self):
        FilterSet, Form = self.make_em(StudyFilterSet)

        f1_value = 'global warming'
        f2_value = 'climate change'
        query_data = [
            'or',
            [
                ['name', {'lookup': 'icontains', 'value': f1_value}],
                ['name', {'lookup': 'icontains', 'value': f2_value}],
            ],
        ]
        data = MultiValueDict(
            [
                ('name__icontains', [f1_value, f2_value]),
            ]
        )
        filterset = FilterSet(deepcopy(query_data))
        form = Form(filterset, data)

        self.assert_form_is_disabled(form)
        self.try_using_disabled_form(form)

    def test_form_disabled__with_nested_filters(self):
        FilterSet, Form = self.make_em(StudyFilterSet)

        f1_value = 'global warming'
        f2_value = 'climate change'
        query_data = [
            'and',
            [
                [
                    'or',
                    [
                        ['name', {'lookup': 'icontains', 'value': f1_value}],
                        ['name', {'lookup': 'icontains', 'value': f2_value}],
                    ],
                ],
                ['continent', {'lookup': 'exact', 'value': 'NA'}],
            ],
        ]
        data = {}
        filterset = FilterSet(deepcopy(query_data))
        form = Form(filterset, data)

        self.assert_form_is_disabled(form)
        self.try_using_disabled_form(form)

    def test_form_disabled__with_not_operator(self):
        FilterSet, Form = self.make_em(StudyFilterSet)

        query_data = [
            'and',
            [
                ['not', ['continent', {'lookup': 'exact', 'value': 'NA'}]],
            ],
        ]
        data = {}
        filterset = FilterSet(deepcopy(query_data))
        form = Form(filterset, data)

        self.assert_form_is_disabled(form)
        self.try_using_disabled_form(form)

    def test_form_hidden_fields(self):
        hidden_fields = ['continent__exact']
        FilterSet, Form = self.make_em(StudyFilterSet, hidden_fields=hidden_fields)

        # Expect the fields to be in the Form's Meta class.
        assert Form.Meta.hidden_fields == hidden_fields

        filterset = FilterSet()
        form = Form(filterset)

        assert isinstance(form.fields['continent__exact'].widget, forms.HiddenInput)

    def test_form_hidden_fields__with_wildcard(self):
        hidden_fields = ['stocked_on*']
        FilterSet, Form = self.make_em(ProductFilterSet, hidden_fields=hidden_fields)

        # Expect the fields to be in the Form's Meta class.
        assert Form.Meta.hidden_fields == hidden_fields

        filterset = FilterSet()
        form = Form(filterset)

        # Expect all 'stocked_on' fields to be hidden.
        assert all(
            isinstance(form.fields[fn].widget, forms.HiddenInput) for fn in form.fields if fn.startswith('stocked_on')
        )

    def test_with_MultiValueField(self):

        class ParticipantFilterSet(FilterSet):
            onboarded = Filter(DateRangeLookup(label="between"), label="Onboarded")

            class Meta:
                model = Participant
                fields = {
                    'name': ['icontains'],
                    'age': ['exact', 'gte'],
                }

        filterset_cls, filter_form_cls = self.make_em(ParticipantFilterSet)
        filterset = filterset_cls(['and', [['name', {'lookup': 'icontains', 'value': 'foo'}]]])
        data = {
            'name__icontains': 'bar',
            'age__gte': '50',
            'onboarded__range_0': '2026-05-08',
            'onboarded__range_1': '2026-04-26',
        }

        # Target
        form = filter_form_cls(filterset, data=data)
        assert not form.errors  # Triggers cleaning and validation

        expected_query_data = [
            'and',
            [
                ['age', {'lookup': 'gte', 'value': '50'}],
                ['name', {'lookup': 'icontains', 'value': 'bar'}],
                ['onboarded', {'lookup': 'range', 'value': ['2026-05-08', '2026-04-26']}],
            ],
        ]
        assert form.filterset.query_data[0] == expected_query_data[0]
        assert sorted(form.filterset.query_data[1]) == expected_query_data[1]

    def test_invalid_form_stops_translation_to_filterset(self, mocker):
        """
        Check that we stop translation when the form contains errors (i.e. invalid).
        When there are errors, the changed field's cleaned data may not be present.
        """
        data = {
            'continent__exact': 'ZZ',  # invalid option
        }
        FilterSet, Form = self.make_em(StudyFilterSet)

        filterset = FilterSet()
        form = Form(filterset, data=data)

        spy = mocker.spy(form, '_translate_to_filterset')
        # Expect the form to have caught the validation error.
        assert 'continent__exact' in form.errors
        # Expect the translation to not have executed due to the presents of errors.
        spy.assert_not_called()

    def sort_query_data_items(self, query_data):
        def gen_sort_key(x):
            return f"{x[0]}-{x[1]['lookup']}-{x[1]['value']}"

        return sorted(query_data[1], key=gen_sort_key)

    def test_relational_attribute_filter(self, mocker):
        """
        Ensure we are able to correctly map the form field to the filter
        given a filter name that contains the attribute name on the referenced model.
        """

        class ParticipantFilterSet(FilterSet):
            facility__max_occupancy = Filter(
                InputLookup('exact', label="is"),
                InputLookup('gte', label="greater than or equal to"),
                InputLookup('lte', label="less than or equal to"),
                label="Facility max occupancy",
            )

            class Meta:
                model = Participant
                fields = {
                    'name': ['icontains'],
                    'age': ['exact', 'gte'],
                    'facility__max_occupancy': ['exact', 'gte', 'lte'],
                }

        filterset_cls, filter_form_cls = self.make_em(ParticipantFilterSet)
        filterset = filterset_cls()
        data = {
            'name__icontains': 'bar',
            'age__gte': '50',
            'facility__max_occupancy__gte': '12',
            'facility__max_occupancy__lte': '20',
        }

        # Target
        form = filter_form_cls(filterset, data=data)
        assert not form.errors  # Triggers cleaning and validation

        expected_query_data = [
            'and',
            [
                ['age', {'lookup': 'gte', 'value': '50'}],
                ['facility__max_occupancy', {'lookup': 'gte', 'value': '12'}],
                ['facility__max_occupancy', {'lookup': 'lte', 'value': '20'}],
                ['name', {'lookup': 'icontains', 'value': 'bar'}],
            ],
        ]
        assert form.filterset.query_data[0] == expected_query_data[0]
        assert self.sort_query_data_items(form.filterset.query_data) == expected_query_data[1]

    def test_relational_filter_with_attribute_in_lookup(self):
        """
        Ensure we are able to correctly map the form field to the filter
        given a filter name is a relational field and the lookup references
        an attribute name on the referenced model along with the lookup.
        """

        class ParticipantFilterSet(FilterSet):
            facility = Filter(
                InputLookup('max_occupancy__gte', label="max occupancy greater than or equal to"),
                InputLookup('managed_by__name__icontains', label="managed by name contains"),
                label="Facility",
            )

            class Meta:
                model = Participant
                fields = {
                    'name': ['icontains'],
                    'age': ['exact', 'gte'],
                }

        filterset_cls, filter_form_cls = self.make_em(ParticipantFilterSet)
        filterset = filterset_cls()
        data = {
            'name__icontains': 'bar',
            'age__gte': '50',
            'facility__max_occupancy__gte': '12',
            'facility__managed_by__name__icontains': 'jess',
        }

        # Target
        form = filter_form_cls(filterset, data=data)
        assert not form.errors  # Triggers cleaning and validation

        expected_query_data = [
            'and',
            [
                ['age', {'lookup': 'gte', 'value': '50'}],
                ['facility', {'lookup': 'managed_by__name__icontains', 'value': 'jess'}],
                ['facility', {'lookup': 'max_occupancy__gte', 'value': '12'}],
                ['name', {'lookup': 'icontains', 'value': 'bar'}],
            ],
        ]
        assert form.filterset.query_data[0] == expected_query_data[0]
        assert self.sort_query_data_items(form.filterset.query_data) == expected_query_data[1]

    def test_issue_with_bool_value_choices(self):
        """
        Ensures use of `NullBooleanField` form field in the `YesNoChoiceLookup` results in boolean type value.
        """

        class ParticipantFilterSet(FilterSet):
            is_paid = Filter(
                YesNoChoiceLookup(),
                label="Is paid?",
            )

            class Meta:
                model = Participant
                fields = {
                    'name': ['icontains'],
                    'age': ['exact', 'gte'],
                }

        filterset_cls, filter_form_cls = self.make_em(ParticipantFilterSet)
        filterset = filterset_cls()
        data = {
            'name__icontains': 'bar',
            'age__gte': '50',
            'is_paid__exact': 'True',
        }

        # Target
        form = filter_form_cls(filterset, data=data)
        assert not form.errors  # Triggers cleaning and validation

        expected_query_data = [
            'and',
            [
                ['age', {'lookup': 'gte', 'value': '50'}],
                ['is_paid', {'lookup': 'exact', 'value': True}],
                ['name', {'lookup': 'icontains', 'value': 'bar'}],
            ],
        ]
        assert form.filterset.query_data[0] == expected_query_data[0]
        assert self.sort_query_data_items(form.filterset.query_data) == expected_query_data[1]
