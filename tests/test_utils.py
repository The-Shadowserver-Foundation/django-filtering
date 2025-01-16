from django_filtering.utils import merge_dicts


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
