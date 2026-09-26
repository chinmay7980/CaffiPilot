"""Text-only LLM adapter with OpenAI-compatible endpoint support, bounded retries, and strict error handling."""

import asyncio
import json
import logging
import os
import random
from typing import Any, Dict, List, Optional
import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    AsyncOpenAI,
    AuthenticationError as OpenAIAuthError,
    RateLimitError as OpenAIRateLimitError,
)

from harness.config import settings
from harness.llm.base import (
    APIError,
    AuthenticationError,
    BaseLLMClient,
    ChatMessage,
    InvalidResponseError,
    LLMResponse,
    LLMTimeoutError,
    RateLimitError,
    ToolCallDefinition,
)
from harness.llm.token_counter import estimate_messages_tokens, estimate_tokens

logger = logging.getLogger(__name__)


class LLMAdapter(BaseLLMClient):
    """Production-grade text-only LLM client for OpenAI-compatible providers.

    Features:
    - Reads credentials strictly from AI_API_KEY (or constructor parameter).
    - Preserves configured model without silent fallbacks.
    - Handles text generation, tool calls, JSON argument parsing.
    - Implements exponential backoff with jitter for rate limits and transient 5xx errors.
    - Converts provider exceptions into standardized LLMException types.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        allow_mock_fallback: bool = False,
    ):
        raw_key = api_key if api_key is not None else (settings.ai_api_key or os.getenv("AI_API_KEY", ""))
        self.api_key = raw_key.strip()
        self.model = (model or settings.ai_model or os.getenv("AI_MODEL", "gpt-4o")).strip()
        if base_url and base_url.strip():
            self.base_url = base_url.strip()
        elif self.model.lower().startswith("gemini"):
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        else:
            self.base_url = (settings.effective_base_url or "https://api.openai.com/v1").strip()
        self.timeout = timeout
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.allow_mock_fallback = allow_mock_fallback

        self._client: Optional[AsyncOpenAI] = None
        if self.api_key and self.api_key != "your_api_key_here":
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
                max_retries=0,  # We handle retries with explicit jittered backoff
            )

    @property
    def is_authenticated(self) -> bool:
        """Returns True if a non-placeholder API key is configured."""
        return bool(self.api_key and self.api_key != "your_api_key_here")

    def _validate_credentials(self) -> None:
        """Ensures credentials exist; raises AuthenticationError otherwise."""
        if not self.is_authenticated:
            if self.allow_mock_fallback:
                return
            raise AuthenticationError(
                f"Missing or invalid AI_API_KEY. Please set the AI_API_KEY environment variable "
                f"to authenticate with model '{self.model}'.",
                provider="openai-compatible",
                model=self.model,
            )

    async def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Generates a model response with structured tool calls and robust error handling."""
        self._validate_credentials()

        if not self.is_authenticated and self.allow_mock_fallback:
            logger.warning(
                f"Running model '{self.model}' in mock offline mode (AI_API_KEY not configured)."
            )
            return self._generate_offline_mock(messages)

        formatted_messages = [msg.to_openai_dict() for msg in messages]

        # Enforce text-only content
        for msg_dict in formatted_messages:
            if "content" in msg_dict and msg_dict["content"] is not None:
                msg_dict["content"] = str(msg_dict["content"])

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
        }

        if tools and len(tools) > 0:
            payload["tools"] = tools
            # Omit tool_choice="auto" for local Ollama endpoints to prevent 400 invalid tool arguments
            if "127.0.0.1" not in self.base_url and "localhost" not in self.base_url:
                payload["tool_choice"] = "auto"

        # Execute call with bounded retries and exponential backoff
        return await self._execute_with_retry(payload, formatted_messages)

    async def _execute_with_retry(
        self, payload: Dict[str, Any], formatted_messages: List[Dict[str, Any]]
    ) -> LLMResponse:
        """Executes chat completion with exponential backoff on transient errors."""
        last_exception: Optional[Exception] = None
        backoff = self.initial_backoff

        for attempt in range(1 + self.max_retries):
            try:
                assert self._client is not None
                raw_response = await asyncio.wait_for(
                    self._client.chat.completions.create(**payload),
                    timeout=self.timeout,
                )
                return self._parse_response(raw_response, formatted_messages)

            except asyncio.TimeoutError:
                last_exception = LLMTimeoutError(
                    f"Request to model '{self.model}' timed out after {self.timeout}s (attempt {attempt + 1}/{self.max_retries + 1}).",
                    provider="openai-compatible",
                    model=self.model,
                )
                logger.warning(str(last_exception))

            except OpenAIRateLimitError as e:
                last_exception = RateLimitError(
                    f"Rate limit exceeded (429) on model '{self.model}': {str(e)}",
                    provider="openai-compatible",
                    model=self.model,
                )
                logger.warning(f"{last_exception} — Retrying in {backoff:.2f}s...")

            except OpenAIAuthError as e:
                # Fatal authentication error: do not retry
                raise AuthenticationError(
                    f"Authentication failed for model '{self.model}': {str(e)}",
                    provider="openai-compatible",
                    model=self.model,
                ) from e

            except APIStatusError as e:
                status = e.status_code
                if status in (500, 502, 503, 504, 529):
                    last_exception = APIError(
                        f"Transient server error ({status}) from model provider: {str(e)}",
                        provider="openai-compatible",
                        model=self.model,
                    )
                    logger.warning(f"{last_exception} — Retrying in {backoff:.2f}s...")
                else:
                    # Non-transient 4xx error (e.g., 400 Bad Request)
                    raise APIError(
                        f"API request rejected with status {status}: {str(e)}",
                        provider="openai-compatible",
                        model=self.model,
                    ) from e

            except APIConnectionError as e:
                last_exception = APIError(
                    f"Network connection failure while connecting to model endpoint: {str(e)}",
                    provider="openai-compatible",
                    model=self.model,
                )
                logger.warning(f"{last_exception} — Retrying in {backoff:.2f}s...")

            except Exception as e:
                if isinstance(e, (AuthenticationError, APIError, RateLimitError, LLMTimeoutError, InvalidResponseError)):
                    raise e
                raise APIError(
                    f"Unexpected error communicating with model '{self.model}': {str(e)}",
                    provider="openai-compatible",
                    model=self.model,
                ) from e

            if attempt < self.max_retries:
                # Apply jittered exponential backoff
                jitter = random.uniform(0.5, 1.5)
                await asyncio.sleep(backoff * jitter)
                backoff *= 2.0

        assert last_exception is not None
        raise last_exception

    def _parse_response(
        self, response: Any, formatted_messages: List[Dict[str, Any]]
    ) -> LLMResponse:
        """Validates and parses the raw completion response into an LLMResponse."""
        if not response or not hasattr(response, "choices") or not response.choices:
            raise InvalidResponseError(
                f"Model '{self.model}' returned an invalid response with empty choices.",
                provider="openai-compatible",
                model=self.model,
            )

        choice = response.choices[0]
        message = getattr(choice, "message", None)
        if message is None:
            raise InvalidResponseError(
                f"Model '{self.model}' returned a choice with missing message payload.",
                provider="openai-compatible",
                model=self.model,
            )

        tool_calls: List[ToolCallDefinition] = []
        if getattr(message, "tool_calls", None):
            for i, tc in enumerate(message.tool_calls):
                func = getattr(tc, "function", None)
                func_name = str(getattr(func, "name", "unknown_tool")) if func else "unknown_tool"
                raw_args = getattr(func, "arguments", "{}") if func else "{}"

                parsed_args: Dict[str, Any] = {}
                if isinstance(raw_args, dict):
                    parsed_args = raw_args
                elif isinstance(raw_args, str):
                    try:
                        parsed_args = json.loads(raw_args) if raw_args.strip() else {}
                    except json.JSONDecodeError as err:
                        logger.error(f"Malformed JSON arguments in tool call '{func_name}': {raw_args} ({err})")
                        # Include raw_arguments fallback so validator can catch and report cleanly
                        parsed_args = {"_raw_arguments_malformed": raw_args, "_error": str(err)}

                tool_calls.append(
                    ToolCallDefinition(
                        id=str(getattr(tc, "id", f"call_{i}")),
                        name=func_name,
                        arguments=parsed_args,
                    )
                )

        content_val = str(message.content) if message.content is not None else None
        
        # Fallback: if no native tool_calls, detect if content is a JSON tool call
        if not tool_calls and content_val:
            clean_content = content_val.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            elif clean_content.startswith("```"):
                clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            clean_content = clean_content.strip()

            if clean_content.startswith("{") and clean_content.endswith("}"):
                try:
                    data = json.loads(clean_content)
                    if isinstance(data, dict):
                        tool_name = data.get("name") or data.get("tool") or data.get("function")
                        tool_args = data.get("arguments") or data.get("parameters") or {}
                        if tool_name and isinstance(tool_name, str):
                            if not isinstance(tool_args, dict):
                                tool_args = {}
                            tool_calls.append(
                                ToolCallDefinition(
                                    id=f"call_text_{len(tool_calls)}",
                                    name=tool_name,
                                    arguments=tool_args,
                                )
                            )
                except Exception:
                    pass

        finish_val = str(getattr(choice, "finish_reason", "stop") or "stop")
        model_val = str(getattr(response, "model", self.model) or self.model)

        prompt_tokens = (
            int(response.usage.prompt_tokens)
            if hasattr(response, "usage") and response.usage and hasattr(response.usage, "prompt_tokens")
            else estimate_messages_tokens(formatted_messages)
        )
        completion_tokens = (
            int(response.usage.completion_tokens)
            if hasattr(response, "usage") and response.usage and hasattr(response.usage, "completion_tokens")
            else estimate_tokens(content_val or "")
        )
        total_tokens = (
            int(response.usage.total_tokens)
            if hasattr(response, "usage") and response.usage and hasattr(response.usage, "total_tokens")
            else (prompt_tokens + completion_tokens)
        )

        return LLMResponse(
            content=content_val,
            tool_calls=tool_calls,
            finish_reason=finish_val,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model_val,
        )

    def _generate_offline_mock(self, messages: List[ChatMessage]) -> LLMResponse:
        """Generates a fallback mock response when in offline simulation mode."""
        tokens = estimate_messages_tokens(messages)
        content = f"Offline mock response for model '{self.model}'."
        return LLMResponse(
            content=content,
            tool_calls=[],
            finish_reason="stop",
            prompt_tokens=tokens,
            completion_tokens=10,
            total_tokens=tokens + 10,
            model=f"{self.model}-offline",
        )
