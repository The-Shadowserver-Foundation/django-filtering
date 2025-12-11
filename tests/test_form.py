from copy import deepcopy
from django import forms
from django.utils.datastructures import MultiValueDict

from django_filtering.filters import (
    ChoiceLookup,
    DateRangeLookup,
    Filter,
    InputLookup,
)
from django_filtering.filterset import FilterSet
from django_filtering.form import flat_filtering_form_factory, FlatFilteringForm

from tests.lab_app.filters import StudyFilterSet
from tests.market_app.filters import TopBrandKitchenProductFilterSet


class TestLookupToFormField:

    def test_InputLookup(self):
        lookup = InputLookup("iexact", label="is")
        filter = Filter(lookup, label="Name")
        filter = filter.bind("name")

        form_fields = filter.as_form_fields()
        assert len(form_fields) == 1
        assert isinstance(form_fields[f"{filter.name}__{lookup.name}"], forms.CharField)

    def test_ChoiceLookup(self):
        choices = [("y", "Yes"), ("n", "No")]
        lookup = ChoiceLookup("exact", choices=choices)
        filter = Filter(lookup, label="Category")
        filter = filter.bind("category")

        form_fields = filter.as_form_fields()
        assert len(form_fields) == 1
        form_field = form_fields[f"{filter.name}__{lookup.name}"]
        assert isinstance(form_field, forms.ChoiceField)
        assert form_field.choices == choices

    def test_DateRangeLookup(self):
        lookup = DateRangeLookup("range", label="between")
        filter = Filter(lookup, label="Created")
        filter = filter.bind("created")

        form_fields = filter.as_form_fields()
        assert len(form_fields) == 2
        assert all(isinstance(f, forms.DateField) for f in form_fields.values())
        lte_form_field, gte_form_field = form_fields
        assert 'created__range__lte' in form_fields
        assert 'created__range__gte' in form_fields


class TestFilterSetFormAdaptation:

    def make_em(self, FilterSet):
        return FilterSet, flat_filtering_form_factory(FilterSet)

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
        assert Form.__name__ == f"{FilterSet.__name__}FlatFilteringForm"

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

        # Expect the initial values to be set from the filterset's query data.
        expected_initial = {
            'category__exact': f1_value,
            'brand__exact': filterset.get_filter('brand').sticky_value,
        }

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
        expected_error_message = [
            "The form is disabled when nested filters "
            "or non-'and' operations are used."
        ]
        assert form.errors['__all__'] == expected_error_message

    def assert_form_is_disabled(self, form):
        # Expect the form to know it is not enabled.
        assert form.is_enabled == False

        # Expect the initial values to be unset.
        assert form.initial == {}

        # Expect all form fields to be disabled
        assert all([f.disabled for f in form.fields.values()])

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
        data = MultiValueDict([
            ('name__icontains', [f1_value, f2_value]),
        ])
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
                    'or', [
                        ['name', {'lookup': 'icontains', 'value': f1_value}],
                        ['name', {'lookup': 'icontains', 'value': f2_value}]
                    ]
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
