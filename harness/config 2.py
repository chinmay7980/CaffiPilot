"""Configuration settings for the AI Coding Harness using Pydantic Settings."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # LLM Settings (Strictly reads from AI_API_KEY and AI_MODEL)
    ai_api_key: str = Field(
        default_factory=lambda: os.getenv("AI_API_KEY", ""),
        description="API Key for the LLM provider (reads from AI_API_KEY)",
    )
    ai_model: str = Field(
        default_factory=lambda: os.getenv("AI_MODEL", "gpt-4o"),
        description="Prescribed LLM model name (e.g., gpt-4o, gemini-2.0-flash, gemini-1.5-flash, claude-3-5-sonnet-20241022)",
    )
    ai_base_url: str = Field(
        default_factory=lambda: os.getenv("AI_BASE_URL", ""),
        description="Optional base URL for OpenAI-compatible LLM endpoints",
    )

    # Server Settings
    harness_host: str = Field(
        default="0.0.0.0",
        description="FastAPI Host bind address",
    )
    harness_port: int = Field(
        default=8000,
        description="FastAPI Port bind address",
    )

    # Execution Bounds & Safety
    harness_max_steps: int = Field(
        default=35,
        description="Maximum autonomous iterations per coding task before terminating",
    )
    harness_command_timeout: int = Field(
        default=60,
        description="Timeout in seconds for terminal command execution",
    )
    harness_max_context_tokens: int = Field(
        default=32000,
        description="Maximum token budget for prompt and context history window",
    )
    harness_log_level: str = Field(
        default="INFO",
        description="Logging verbosity level (DEBUG, INFO, WARNING, ERROR)",
    )

    @property
    def effective_base_url(self) -> str:
        """Resolves the base URL, auto-routing Gemini models to Google's OpenAI-compatible endpoint."""
        if self.ai_base_url and self.ai_base_url.strip():
            return self.ai_base_url.strip()
        if self.ai_model.lower().startswith("gemini"):
            return "https://generativelanguage.googleapis.com/v1beta/openai/"
        return "https://api.openai.com/v1"

    @property
    def has_valid_api_key(self) -> bool:
        """Returns True if a non-placeholder API key is set."""
        key = self.ai_api_key.strip()
        return bool(key and key != "your_api_key_here")


# Singleton instance
settings = Settings()
