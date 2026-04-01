import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_default_cors_allowed_origins_are_local_vite_hosts():
    settings = Settings(_env_file=None)

    assert settings.cors_allowed_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]


def test_settings_supports_csv_cors_allowed_origins():
    settings = Settings(
        _env_file=None,
        cors_allowed_origins="http://localhost:5173, http://127.0.0.1:5173",
    )

    assert settings.cors_allowed_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_settings_supports_json_cors_allowed_origins():
    settings = Settings(
        _env_file=None,
        cors_allowed_origins='["http://localhost:5173", "https://admin.example.com"]',
    )

    assert settings.cors_allowed_origins == [
        "http://localhost:5173",
        "https://admin.example.com",
    ]


def test_settings_requires_secure_user_session_cookie_in_production():
    with pytest.raises(ValidationError, match="USER_SESSION_COOKIE_SECURE must be true"):
        Settings(
            _env_file=None,
            app_env="production",
            user_session_cookie_secure=False,
        )


def test_settings_allows_secure_user_session_cookie_in_production():
    settings = Settings(
        _env_file=None,
        app_env="production",
        user_session_cookie_secure=True,
    )

    assert settings.app_env == "production"
    assert settings.user_session_cookie_secure is True
