"""Unit tests for configuration loading and validation."""

import os
import pytest
from harness.config import Settings


def test_default_settings():
    """Verify default setting values."""
    settings = Settings()
    assert isinstance(settings.ai_model, str)
    assert len(settings.ai_model) > 0
    assert settings.harness_host == "0.0.0.0"
    assert settings.harness_port == 8000
    assert settings.harness_max_steps >= 20
    assert settings.harness_command_timeout >= 30


def test_has_valid_api_key():
    """Verify validation helper."""
    s1 = Settings(ai_api_key="your_api_key_here")
    assert not s1.has_valid_api_key

    s2 = Settings(ai_api_key="")
    assert not s2.has_valid_api_key

    s3 = Settings(ai_api_key="sk-real-secret-key-123")
    assert s3.has_valid_api_key
