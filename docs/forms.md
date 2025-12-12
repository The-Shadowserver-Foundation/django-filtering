# Flat FilterSet Form

FilterSet's are designed with nesting conditions in mind. But a shim implementation to provide a flat form for one left of nested data is available in `django_filtering.form`.

The basic usage is as follows:

```python
import json
from urllib.parse import urlencode

from django.shortcuts import render, reverse
from django_filtering.form import (
    flat_filtering_form_factory,
    
)

from .filters import PostFilterSet

FilteringForm = filtering_form_factory()
FlatFilterForm = flat_filtering_from(PostFilterSet)

def posts_list(request):
    data = getattr(request, request.method)
    filtering_form = FilteringForm(data)
    if not filtering_form.is_valid():
        raise Exception('out of scope for this example')

    filterset = PostFilterSet(filtering_form.cleaned_data['q'])

    if request.method in ('POST', 'PUT',):
        form = FlatFilterForm(filterset, data)
        if not form.errors:
            url = reverse(posts_list)
            qs = urlencode({'q': json.dumps(form.filterset.query_data)})
            url = f"{url}?{qs}"
            return redirect(url)
        # Else you can decide to show the form errors
        # in the rendered template.
    else:
        # Initializes the form's `initial` from the filterset.
        form = FlatFilterForm(filterset)

    objects = filterset.filter_queryset()
    context = {
        'filterset': filterset,
        'form': form,
        'objects': objects,
    }
    return render(request, 'posts/list.html', context=context)
```

In this example the `FlatFilterForm` is created from the `PostFilterSet`. All the filterset's filters are made into equivalent form fields.

The instantiated form has an `is_enabled` property. This indicate if the form is enabled. The form is disabled when the top-level operator is anything other than 'and' or there are nested conditions in the query data. When the form is disabled, all the field's widgets will be disabled as well. The reason the form is only enabled when the 'and' operator and one level of conditions are in use is because the user can't intuitively reason about what will happen otherwise.
