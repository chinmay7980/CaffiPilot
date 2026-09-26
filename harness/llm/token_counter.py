"""Token estimation utilities for context budgeting and monitoring."""

from typing import Any, List, Union


def estimate_tokens(text: Union[str, Any]) -> int:
    """Estimates the number of tokens in a string or object.

    Uses an average heuristic of ~4 characters per token for English/code text,
    ensuring lightweight and fast context budgeting without hard dependency on specific tokenizer binaries.
    """
    if not isinstance(text, str):
        text = str(text)
    if not text:
        return 0
    # Heuristic: 1 token ~= 4 chars, with a minimum of 1 token for non-empty text
    return max(1, (len(text) + 3) // 4)


def estimate_messages_tokens(messages: List[Any]) -> int:
    """Estimates total token count for a list of chat message objects or dicts."""
    total = 0
    for msg in messages:
        if isinstance(msg, dict):
            content = msg.get("content", "") or ""
            role = msg.get("role", "")
            total += 4 + estimate_tokens(content) + estimate_tokens(role)
            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    total += estimate_tokens(str(tc))
        else:
            content = getattr(msg, "content", "") or ""
            role = getattr(msg, "role", "") or ""
            total += 4 + estimate_tokens(content) + estimate_tokens(role)
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                total += estimate_tokens(str(tool_calls))
    return total + 2  # priming tokens
