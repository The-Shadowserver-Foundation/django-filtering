from django.db.models import Q

from django_filtering.utils import (
    construct_field_lookup_arg,
    deconstruct_query,
    merge_dicts,
)


def test_merge_dicts():
    merging = [{'a': 1, 'z': 1}, {'b': 2, 'y': 2}, {'c': 3, 'x': 3}, {'z': 4, 'y': 4}]
    expected = {'a': 1, 'b': 2, 'c': 3, 'x': 3, 'z': 4, 'y': 4}
    assert merge_dicts(*merging) == expected

def test_merge_dicts__with_one_arg():
    expected = merging = [{'a': 1, 'z': 1}]
    expected = {'a': 1, 'z': 1}
    assert merge_dicts(*merging) == expected


def test_merge_dicts__with_no_args():
    expected = merging = []
    expected = {}
    assert merge_dicts(*merging) == expected


def test_construct_field_lookup_arg():
    assert construct_field_lookup_arg('state', 'Complete') == ('state', 'Complete')
    assert construct_field_lookup_arg('name', 'foo', 'icontains') == ('name__icontains', 'foo')


def test_deconstruct_field_lookup_arg():
    # Note, when a lookup is not provided, it defaults to 'exact'.
    # Django defaults to 'exact' in the backend. Here we are simply explicit about it.
    expected = ['state', {'lookup': 'exact', 'value': 'Complete'}]
    assert deconstruct_query(Q(state='Complete')) == expected

    expected = ['name', {'lookup': 'icontains', 'value': 'foo'}]
    assert deconstruct_query(Q(name__icontains='foo')) == expected
