from datetime import date

from django import forms

from django_filtering.forms.fields import DateRangeField
from django_filtering.forms.widgets import DateRangeWidget


class SampleForm(forms.Form):
    date_range = DateRangeField()


class TestDateRangeField:
    def test_parses_valid_date_range(self):
        form = SampleForm(
            data={
                'date_range_0': '2024-01-01',
                'date_range_1': '2024-12-31',
            }
        )
        assert form.is_valid(), form.errors
        result = form.cleaned_data['date_range']
        assert result.start == date(2024, 1, 1)
        assert result.stop == date(2024, 12, 31)

    def test_returns_slice(self):
        form = SampleForm(
            data={
                'date_range_0': '2024-01-01',
                'date_range_1': '2024-12-31',
            }
        )
        assert form.is_valid()
        assert isinstance(form.cleaned_data['date_range'], slice)

    def test_invalid_when_start_missing(self):
        form = SampleForm(
            data={
                'date_range_0': '',
                'date_range_1': '2024-12-31',
            }
        )
        assert not form.is_valid()
        assert 'date_range' in form.errors

    def test_invalid_when_end_missing(self):
        form = SampleForm(
            data={
                'date_range_0': '2024-01-01',
                'date_range_1': '',
            }
        )
        assert not form.is_valid()
        assert 'date_range' in form.errors

    def test_invalid_when_both_missing(self):
        form = SampleForm(
            data={
                'date_range_0': '',
                'date_range_1': '',
            }
        )
        assert not form.is_valid()
        assert 'date_range' in form.errors

    def test_invalid_date_format(self):
        form = SampleForm(
            data={
                'date_range_0': 'not-a-date',
                'date_range_1': '2024-12-31',
            }
        )
        assert not form.is_valid()
        assert 'date_range' in form.errors

    def test_compress_returns_none_for_empty(self):
        field = DateRangeField()
        assert field.compress([]) is None

    def test_widget_class(self):
        field = DateRangeField()
        assert isinstance(field.widget, DateRangeWidget)
