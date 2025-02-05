# Django Filtering

A library for filtering Django Models.

The original usecase for this project required the following:

- provides a means of allowing users to filter modeled data
- provides the ability to `AND`, `OR` and `NOT` filters (i.e. operators)
- provides the ability to group filters by operator
- serializes, validates, etc.

A user interface (UI) is available for this package in the
[`django-filtering-ui`](https://github.com/The-Shadowserver-Foundation/django-filtering-ui/)
package.

## Installation

Install via pip or the preferred package manager:

    pip install django-filtering

At this time, this package is more of a library than an installablable app.
So there is no reason to add it to the Django project's `INSTALLED_APPS`.

## Usage

The exposed portions of this package are a class named `FilterSet`
and a factory function named `filterset_factory`.
These are importable via:

    from django_filterset.filters import filterset_factory, FilterSet

Say you have a `Post` model that you want user filters on.
We'd start by creating a `FilterSet` through `filterset_factory`.

    filters = {
        'title': ['icontains'],
        'author': [['fullname', 'iexact'], ['email', 'iexact']],
        'content': ['icontains'],
    }
    PostFilterSet = filterset_factory(Post, filters=filters)

Note, this package does not come with an interface for user filtering.
One is under development, but not yet available for use.
So we'll assume that some form posts or redirects the user to the following url:

    /posts/?q=["and",[["title",{"lookup":"icontains","value":"foo"}],["content",{"lookup":"icontains","value":"bar"}]]

In this case we have a `q` query string value with JSON content,
which we'll come back to in a bit.

Let's say this url is a listing view for `Post` objects, something that looks like:

    def posts_list(request):
        filterset = PostFilterSet(json.dumps(request.GET.get('q')))
        objects = filterset.filter_queryset()
        return HttpResponse('\n'.join([o.get_absolute_url() for o in objects]))

You give the JSON serializable query data to the `FilterSet` and call the `filter_queryset` method to filter the results.

The JSON serialiable query data is a loosely lisp'ish data structure that looks something like:

    query-data := [<operator>, [<filter|operator>,...]]
    operator := 'and' | 'or' | 'not' | 'xor'
    filter := [<field-name>, {"lookup": <lookup>, "value": <value>}]
    field-name := string
    lookup := string | array[string]
    value := string

## State of development

This package is very much a work-in-progress. All APIs are completely unstable.

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

© 2024 The Shadowserver Foundation
