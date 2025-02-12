import django


def pytest_configure(config):
    from django.conf import settings

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:'
            },
        },
        DEBUG=True,
        INSTALLED_APPS=[
            "django_filtering",
            "tests.lab_app",
            "tests.market_app",
        ],
    )

    django.setup()
