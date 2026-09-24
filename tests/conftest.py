import django


def pytest_configure(config):
    from django.conf import settings

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
        },
        DEBUG=True,
        INSTALLED_APPS=[
            "django_filtering",
            "tests.lab_app",
            "tests.market_app",
            "tests.faux_app",
        ],
        # Use BLANK_CHOICE_DASH to provide backwards compatibility with Django < 6.1.
        USE_BLANK_CHOICE_DASH=True,
    )

    django.setup()
