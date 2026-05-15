from django import forms


class DateRangeWidget(forms.MultiWidget):
    template_name = 'django_filtering/forms/widgets/date_range.html'

    def __init__(self, attrs=None):
        widgets = [
            forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        ]
        super().__init__(widgets, attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # Render the widgets separate so that the widget's default renderer is used.
        context['rendered_widgets'] = [
            widget.render(f'{name}_{i}', context['widget']['subwidgets'][i]['value'], attrs)
            for i, widget in enumerate(self.widgets)
        ]
        return context

    def decompress(self, value):
        if value:
            return [value.start, value.stop]
        return [None, None]
