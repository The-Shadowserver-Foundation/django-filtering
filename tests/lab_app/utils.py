from django.db.models import Q


CONTINENT_CHOICES = [
    ('AS', 'Asia'),
    ('AF', 'Africa'),
    ('NA', 'North America'),
    ('SA', 'South America'),
    ('AN', 'Antarctica'),
    ('EU', 'Europe'),
    ('AU', 'Australia'),
]

CONTINENT_COUNTRIES_MAP = {
    # An incomplete list of ISO 3166-1 alpha-3 country codes for North America
    'NA': ['CAN', 'MEX', 'USA', 'BMU', 'GRL']
}

def continent_to_countries(value, queryset, **kwargs) -> Q:
    if value != 'NA':
        raise Exception("Testing scope is limited to the 'NA' choice.")
    return Q(country__in=CONTINENT_COUNTRIES_MAP[value])
