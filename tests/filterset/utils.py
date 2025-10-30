from django_filtering import FilterSet


def get_filter_lookup_mapping(filterset: FilterSet) -> dict[str, list[str]]:
    """
    Returns a mapping of filter names to lookup names.
    """
    return {
        filter.name: [lookup.name for lookup in filter.lookups]
        for filter in filterset.filters
    }
