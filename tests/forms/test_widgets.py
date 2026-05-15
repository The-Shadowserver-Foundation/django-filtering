from datetime import date

from django_filtering.forms.widgets import DateRangeWidget


class TestDateRangeWidget:
    def test_decompresses_slice_into_start_and_end(self):
        widget = DateRangeWidget()
        value = slice(date(2024, 1, 1), date(2024, 12, 31))
        assert widget.decompress(value) == [date(2024, 1, 1), date(2024, 12, 31)]

    def test_decompresses_none_into_two_nones(self):
        widget = DateRangeWidget()
        assert widget.decompress(None) == [None, None]

    def test_renders_with_mdash(self, rf):
        widget = DateRangeWidget()
        rendered = widget.render('daterange', [None, None])
        assert '&mdash;' in rendered or '—' in rendered

    def test_subwidgets_have_type_date(self):
        widget = DateRangeWidget()
        assert widget.widgets[0].input_type == 'date'
        assert widget.widgets[1].input_type == 'date'

    def test_renders_with_values(self):
        widget = DateRangeWidget()
        value = slice(date(2024, 1, 1), date(2024, 12, 31))
        name = 'daterange'
        expected = (
            f'<input type="date" name="{name}_0" value="{value.start.isoformat()}">'
            '<span>—</span>'
            f'<input type="date" name="{name}_1" value="{value.stop.isoformat()}">'
        )
        assert widget.render(name, value) == expected
