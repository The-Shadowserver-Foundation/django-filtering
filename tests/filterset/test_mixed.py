import pytest

from .utils import get_filter_lookup_mapping


class TestFilterSetCreation:
    """
    Test the construction of a FilterSet class.
    """

    @pytest.mark.skip(reason="Incomplete")
    def test_mixed_filters(self):
        """
        Tests the creation of a FilterSet with field and non-field filters.
        """

        # FIXME Make a new filterset that subclasses a filterset
        #       from a model defined in this test.

        expected_filters = {
            "name": ["icontains"],
            "continent": ["exact"],
        }

        # Expect subclass to have Meta class attribute,
        # even though the class doesn't define it.
        assert not hasattr(filterset_cls, 'Meta')

        # Expect subclasses of the FilterSet to carry over the filters defined on the superclass.
        assert [name for name in filterset_cls._meta.filters] == list(expected_filters.keys())

        # Check for the expected filters and lookups
        filterset = filterset_cls()
        assert get_filter_lookup_mapping(filterset) == expected_filters
