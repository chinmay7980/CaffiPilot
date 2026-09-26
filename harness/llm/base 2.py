"""Abstract base classes, data structures, and exception hierarchy for LLM clients."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# LLM Exception Hierarchy
# ==============================================================================

class LLMException(Exception):
    """Base exception for all LLM provider and adapter errors."""

    def __init__(self, message: str, provider: str = "", model: str = ""):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.model = model


class AuthenticationError(LLMException):
    """Raised when AI_API_KEY is missing, empty, or rejected by the provider."""
    pass


class RateLimitError(LLMException):
    """Raised when provider rate limits / 429 are encountered and retries are exhausted."""
    pass


class LLMTimeoutError(LLMException):
    """Raised when an API request to the model times out."""
    pass


class InvalidResponseError(LLMException):
    """Raised when the model response is malformed or unparseable."""
    pass


class APIError(LLMException):
    """Raised when provider returns a non-transient 4xx or fatal 5xx error."""
    pass


# ==============================================================================
# Data Structures
# ==============================================================================

class ToolCallDefinition(BaseModel):
    """Structured representation of a model-requested tool execution."""

    id: str = Field(description="Unique tool call identifier")
    name: str = Field(description="Name of the tool to invoke")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Parsed JSON arguments for the tool"
    )


class ChatMessage(BaseModel):
    """A single message in the conversation history."""

    role: str = Field(description="Role: system, user, assistant, or tool")
    content: Optional[str] = Field(default=None, description="Textual content")
    name: Optional[str] = Field(
        default=None, description="Tool name if role is 'tool'"
    )
    tool_call_id: Optional[str] = Field(
        default=None, description="Tool call ID if responding to a tool request"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Assistant tool calls if generated"
    )

    def to_openai_dict(self) -> Dict[str, Any]:
        """Serializes message to standard OpenAI text chat format."""
        msg: Dict[str, Any] = {"role": self.role}
        if self.content is not None:
            msg["content"] = str(self.content)
        if self.name is not None:
            msg["name"] = self.name
        if self.tool_call_id is not None:
            msg["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            msg["tool_calls"] = self.tool_calls
        return msg


class LLMResponse(BaseModel):
    """Standardized response from an LLM adapter call."""

    content: Optional[str] = Field(default=None, description="Assistant textual output")
    tool_calls: List[ToolCallDefinition] = Field(
        default_factory=list, description="Requested tool invocations"
    )
    finish_reason: Optional[str] = Field(
        default="stop", description="Model stop reason (stop, tool_calls, length, etc.)"
    )
    prompt_tokens: int = Field(default=0, description="Tokens used for prompt")
    completion_tokens: int = Field(default=0, description="Tokens used for completion")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    model: str = Field(default="", description="Model name that generated the response")


class BaseLLMClient(ABC):
    """Abstract interface for LLM clients."""

    model: str

    @abstractmethod
    async def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Generates a response from the model given the message history and tool schemas."""
        pass
