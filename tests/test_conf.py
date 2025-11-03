import pytest

from django_filtering.conf import _APP_SETTINGS_KEY, settings as filtering_settings


def test_invalid_setting():
    setting = 'FOO'
    with pytest.raises(AttributeError, match=f"Invalid setting name: '{setting}'"):
        getattr(filtering_settings, setting)

def test_settings_modification(settings):
    expected_setting = {'exact': 'equals'}
    setattr(settings, _APP_SETTINGS_KEY, {"LOOKUP_LABELS": expected_setting})

    assert filtering_settings.LOOKUP_LABELS == expected_setting
