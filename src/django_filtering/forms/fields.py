from django import forms

from .widgets import DateRangeWidget


class DateRangeField(forms.MultiValueField):
    widget = DateRangeWidget

    def __init__(self, *args, **kwargs):
        fields = (
            forms.DateField(label='Start date', required=False),
            forms.DateField(label='End date', required=False),
        )
        kwargs.setdefault('fields', fields)
        kwargs.setdefault('require_all_fields', True)
        super().__init__(*args, **kwargs)

    def compress(self, data_list):
        if not data_list:
            return None
        start = data_list[0] if data_list else None
        end = data_list[1] if len(data_list) > 1 else None
        if start and end:
            return slice(start, end)
        return slice(start, end)
