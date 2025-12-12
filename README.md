# Django Filtering

A library for filtering Django Models.

The original usecase for this project required the following:

- provides a means of allowing users to filter modeled data
- provides the ability to group filters by `AND`, `OR` and `NOT` operators
- serializes, validates, etc.

A user interface (UI) is available for this package in the
[`django-filtering-ui`](https://github.com/The-Shadowserver-Foundation/django-filtering-ui/)
package.


## State of development

This package is very much a work-in-progress. All APIs are completely unstable.


## Installation

Install via pip or the preferred package manager:

    pip install django-filtering

At this time, this package is more of a library than an installablable app.
So there is no reason to add it to the Django project's `INSTALLED_APPS`.

## Usage

Say you have a `Post` model that you want users to be able to filter.
We'd start by creating a `FilterSet`.

```python
import django_filtering as filtering

class PostFilterSet(filtering.FilterSet):
    title = filtering.Filter(
        filtering.InputLookup('icontains', label="contains"),
        label="Title",
    )
    author = filtering.Filter(
        filtering.InputLookup('fullname__iexact', label="fullname is"),
        filtering.InputLookup('email__iexact', label="email is"),
        label="Author",
    )
    content = filtering.Filter(
        filtering.InputLookup('icontains', label="contains"),
        label="Content",
    )

    class Meta:
        model = Post
```

This can also be expressed using the declarative style:

```python
class PostFilterSet(filtering.FilterSet):
    class Meta:
        model = Post
        fields = {
            'title': ['icontains'],
            'author': ['fullname__iexact', 'email__iexact'],
            'content': ['icontains'],
        }
```

Note, this package does not come with an interface for user filtering.
The `django-filtering-ui` package does provide an interface.

The filters can be posted in a Form. For example, we'll say we have a form
that has a single `q` JSON field.

```python
q = [
    'and',
    [
        ['title', {'lookup': 'icontains', 'value': 'foo'}],
        ['content', {'lookup': 'icontains', 'value': 'bar'}],
    ]
]
```

The basic structure is an array with an operator and array of further criteria, where that can be a filter array or another operator grouping.

An example of a user posting filters could look like the following url:

    /posts/?q=["and",[["title",{"lookup":"icontains","value":"foo"}],["content",{"lookup":"icontains","value":"bar"}]]

In this case we have a `q` query string value with JSON content.
This query data structure is documented in more detail later in this document.

Let's say this url is a listing view for `Post` objects, something that looks like:

```python
def posts_list(request):
    query_data = json.loads(request.GET.get('q', '[]'))
    filterset = PostFilterSet(query_data)
    queryset = filterset.filter_queryset()
    return HttpResponse('\n'.join([o.get_absolute_url() for o in queryset]))
```

In this example view we use the `PostFilterSet` with the query string value.
We get the fitlered results by calling the `<FilterSet>.filter_queryset` method.

### About the query data structure

The JSON serialiable query data is a loosely lisp'ish data structure that looks something like:

    query-data := [<operator>, [<filter|operator>,...]]
    operator := 'and' | 'or' | 'not' | 'xor'
    filter := [<field-name>, {"lookup": <lookup>, "value": <value>}]
    field-name := string
    lookup := string
    value := any

Note, the `value` can be of any JSON serialiable type.

### Testing

Note, I'm testing within a docker container, because I never run anything locally.
For the moment the container is simply run with:

    docker run --rm --name django-filtering --workdir /code -v $PWD:/code -d python:3.12 sleep infinity

Then I execute commands on the shell within it:

    docker exec django-filtering pip install -e '.[tests]'
    docker exec -it django-filtering bash

Within the container's shell you can now execute `pytest`.


## License

GPL v3 (see `LICENSE` file)


## Copyright

© 2025 The Shadowserver Foundation
