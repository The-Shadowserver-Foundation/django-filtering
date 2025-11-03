from django.conf import settings as django_settings


_APP_SETTINGS_KEY = 'DJANGO_FILTERING'
DEFAULT_LOOKUP_LABELS = {
    "exact": "is",
    "iexact": "is (case insensitive)",
    "contains": "contains",
    "icontains": "contains (case insensitive)",
    "in": "in",
    "gt": "greater than",
    "gte": "greater than or equal to",
    "lt": "less than",
    "lte": "less than or equal to",
    "startswith": "starts with",
    "istartswith": "starts with (case insensitive)",
    "endswith": "ends with",
    "iendswith": "ends with (case insensitive)",
    "range": "between",
    "date": "date is",
    "year": "year is",
    "iso_year": "ISO year is",
    "month": "month is",
    "day": "day is",
    "week": "week is",
    "week_day": "week day is",
    "iso_week_day": "ISO week day is",
    "quarter": "quarter is",
    "time": "time is",
    "hour": "hour is",
    "minute": "minute is",
    "second": "second is",
    "isnull": "is null",
    "regex": "matches (regular expression)",
    "iregex": "matches (case insensitive regular expression)",
}
DEFAULTS = {
    "LOOKUP_LABELS": DEFAULT_LOOKUP_LABELS,
}


class Settings:
    """
    django-filtering app settings
    """

    def __init__(self, defaults: dict[str, str] = DEFAULTS):
        self.defaults = defaults

    @property
    def project_settings(self):
        """
        Convenience method for acquiring the django project settings.
        """
        return getattr(django_settings, _APP_SETTINGS_KEY, {})

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError(f"Invalid setting name: '{attr}'")

        if attr in self.project_settings:
            return self.project_settings[attr]
        else:
            return self.defaults[attr]


settings = Settings()


class Configurator:

    def get_lookup_label(self, lookup_name: str) -> str:
        return settings.LOOKUP_LABELS[lookup_name]


configurator = Configurator()
