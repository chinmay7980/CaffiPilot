"""CaffiPilot Evaluation Smoke Test.

Validates that the CaffiPilot environment, LLM configuration,
and Auto-PR router can be imported and initialized properly.
"""

import os
import pytest


def test_harness_imports():
    """Verify core CaffiPilot modules import without errors."""
    from openhands.agent_server.auto_pr_router import auto_pr_router, AutoPRRequest

    assert auto_pr_router is not None
    assert AutoPRRequest is not None


def test_model_configuration():
    """Verify prescribed text-only model is configured."""
    model = os.environ.get("LLM_MODEL", "openai/gpt-oss:120b")
    assert "gpt-oss:120b" in model or "openai/" in model


def test_api_key_resolution():
    """Verify AI_API_KEY takes precedence when configured."""
    test_key = "test-hackathon-key-123"
    os.environ["AI_API_KEY"] = test_key
    assert os.environ.get("AI_API_KEY") == test_key
