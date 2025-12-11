from functools import cached_property

from django import forms
from django.utils.datastructures import MultiValueDict

from .filters import Filter
from .utils import construct_field_lookup_arg, deconstruct_field_lookup_arg


def filtering_form_factory(query_data_field_name='q', cls_base_name=''):
    """
    Factory for creating a simple form
    that only reads the FilterSet's query data from a form submission.
    """
    form_attrs = {query_data_field_name: forms.JSONField(required=False)}
    return type(
        # name
        f'{cls_base_name}FilteringForm',
        # bases
        (forms.Form,),
        # attrs
        form_attrs,
    )


def flat_filtering_form_factory(FilterSet: type['FilterSet']):
    """
    Factory for creating a form
    that can be used with one level of nested query data.
    """
    form_attrs = {}
    for filter in FilterSet._meta.filters.values():
        form_attrs.update(filter.as_form_fields())
    form_attrs['Meta'] = type('Meta', (), {'sticky_fields': []})
    for filter in FilterSet._meta.sticky_filters.values():
        _fields = filter.as_form_fields()
        form_attrs['Meta'].sticky_fields.extend(x for x in _fields)
        form_attrs.update(_fields)
    return type(
        # name
        f'{FilterSet.__name__}FlatFilteringForm',
        # bases
        (FlatFilteringForm,),
        # attrs
        form_attrs,
    )


class FlatFilteringForm(forms.Form):
    """
    Form for receiving the first level of filters and adapting them to the FilterSet.
    """

    def __init__(self, filterset: 'FilterSet', *args, **kwargs):
        self.filterset = filterset
        super().__init__(*args, **kwargs)
        if self.is_enabled:
            self._populate_initial_from_filterset()
            self._disable_fields_for_multivalue_query_data()

    @property
    def _filterset_has_query_data(self) -> bool:
        """
        Check whether the filterset has query data or an empty structure.
        """
        # FIXME There is a design issue around the 'empty' state of query data.
        qd = self.filterset.query_data
        if not qd:
            return False
        else:
            if len(qd) == 2 and not qd[1]:
                return False
        return True

    @cached_property
    def is_enabled(self) -> bool:
        """
        Indicates when the form is enable or disabled.

        Returns enabled (True) when the filterset's query data is empty

        Returns enabled (True) when there is only one level of filters
        using an 'and' connecting operator.
        A form of filters without clear indication the connecting operator
        is not intuitive.

        Returns disabled (False) when the top level operator is not 'and'.

        Return disabled (False) when the filterset contains nested query data.
        In other words, the user has entered __advanced mode__
        and a flat form interface will no longer accurately represent
        the filtering strategy.

        """
        qd = self.filterset.query_data
        nesting_operators = ('and', 'or', 'not',)
        if not self._filterset_has_query_data:
            return True

        if (
            # Disabled when the operator is anything other than 'and',
            # because expected flat form usage expectation is typically ANDing.
            qd[0] != 'and'
            or
            # Disabled when nested operators are present.
            any([qc for qc in qd[1] if qc[0] in nesting_operators])
        ):
            for field in self.fields.values():
                # Disable the field
                field.disabled = True
            self.initial = {}
            return False

        return True

    def __get_filter_by_field_name(self, field_name) -> Filter:
        filter_name, lookup_exp = field_name.split('__', 1)
        return self.filterset.get_filter(filter_name)

    def _populate_initial_from_filterset(self):
        """
        Populate the form with initial data from the filterset.
        """
        # Infer form field's initial value from the initial query data.
        q = self.filterset.query_data
        if q and len(q) == 2:
            conditions = q[1]
            for q_item in conditions:
                field_name, value = self.__get_field_name_and_value(q_item)
                if field_name not in self.fields:
                    continue
                self.initial[field_name] = value

            # Reverse sticky filters using the sticky fields
            condition_field_names = [self.__get_field_name_and_value(x)[0] for x in conditions]
            for field_name in self.Meta.sticky_fields:
                if field_name not in condition_field_names:
                    filter = self.__get_filter_by_field_name(field_name)
                    self.initial[field_name] = filter.sticky_value

    def _disable_fields_for_multivalue_query_data(self):
        """
        Disables fields when the field appears in the filterset's query data multiple times.
        """
        # Infer form field's initial value from the initial query data.
        q = self.filterset.query_data
        use_counts = MultiValueDict()
        if q and len(q) == 2:
            for q_item in q[1]:
                field_name, value = self.__get_field_name_and_value(q_item)
                use_counts.appendlist(field_name, value)

        # Disable fields that have more than one use in the query data.
        # This is done because the UI can't currently handle more than one value in the form input.
        fields_to_disable = [field for field in use_counts if len(use_counts.getlist(field)) >= 2]
        for field_name in fields_to_disable:
            field = self.fields[field_name]
            # Disable the field
            field.disabled = True
            # Empty its initial value to eliminate confusion
            if field_name in self.initial:
                del self.initial[field_name]

    def __get_field_name_and_value(self, q_item):
        field_name, value = construct_field_lookup_arg(q_item[0], **q_item[1])
        # Some form fields that are 'exact' matching do not use the '__exact' lookup suffix.
        # So we compare the constructed field_name with actual field names.
        if q_item[1].get('lookup', None) == 'exact' and field_name not in self.fields:
            # Essentially drops the `__exact` lookup suffix.
            field_name = q_item[0]
        return field_name, value

    def _format_value(self, field_name, value):
        """
        Format a cleaned value. This is primarily used during translation
        from cleaned data to query data.
        """
        field = self.fields[field_name]
        # Handle the cases where the widget formats the value incorrectly
        # for django-filtering usage.
        if isinstance(field.widget, forms.Select):
            if field.widget.allow_multiple_selected:
                raise NotImplementedError()
            return field.widget.format_value(value)[0]
        else:
            return field.widget.format_value(value)

    def clean(self):
        if not self.is_enabled:
            self.add_error(
                None,
                ("The form is disabled when nested filters "
                 "or non-'and' operations are used."),
            )

        # If necessary, initialize the query data structure.
        if len(self.filterset.query_data) == 0:
            # FIXME Initializing this structure, only to then maybe erase it
            #       at the end of this method is not great.
            self.filterset.query_data = ['and', []]

        for field_name, value in self.cleaned_data.items():
            if field_name not in self.changed_data:
                # Ignore fields that haven't changed.
                continue

            conditions = self.filterset.query_data[1]
            condition_field_names = [self.__get_field_name_and_value(x)[0] for x in conditions]

            is_dropped_field = (
                field_name in condition_field_names
                and
                self.cleaned_data[field_name] in self.fields[field_name].empty_values
            )
            is_sticky_field_with_default_value = (
                field_name in self.Meta.sticky_fields
                and field_name in condition_field_names
            )
            if is_dropped_field or is_sticky_field_with_default_value:
                del self.filterset.query_data[1][condition_field_names.index(field_name)]
                continue

            # Reformat the value to base string form for query data usage.
            formatted_value = self._format_value(field_name, value)
            # Insert or update field in query data.
            field_as_q_value = deconstruct_field_lookup_arg(field_name, formatted_value)

            if field_name not in condition_field_names:
                conditions.append(field_as_q_value)
            else:
                idx = condition_field_names.index(field_name)
                conditions[idx] = field_as_q_value

        # Check if the query data has any conditions.
        if not (self.filterset.query_data and self.filterset.query_data[1]):
            # No conditions; blank the data so an empty structure isn't publically used.
            self.filterset.query_data = []
