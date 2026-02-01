"""Tests for configuration module."""

import os
import pytest
from app.config import Settings


def test_settings_defaults():
    """Test default settings values."""
    settings = Settings()

    assert settings.app_name == "AWS Monitor"
    assert settings.app_env == "development"
    assert settings.debug is False
    assert settings.aws_region == "us-east-1"
    assert "production" in settings.protected_tags


def test_settings_protected_tags_parsing(monkeypatch):
    """Test parsing of protected tags from string."""
    # When passed as environment variable
    monkeypatch.setenv("PROTECTED_TAGS", "prod,staging,critical")
    settings = Settings()
    assert settings.protected_tags == ["prod", "staging", "critical"]


def test_settings_cors_origins_parsing(monkeypatch):
    """Test parsing of CORS origins from string."""
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    settings = Settings()
    assert "http://localhost:3000" in settings.cors_origins
    assert "http://localhost:5173" in settings.cors_origins
