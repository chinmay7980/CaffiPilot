"""Unit tests for context management and token budgeting."""

from harness.engine.context import ContextManager
from harness.llm.token_counter import estimate_tokens


def test_context_addition():
    """Verify message addition and structure."""
    ctx = ContextManager(max_tokens=1000)
    ctx.add_system_message("You are an agent.")
    ctx.add_user_message("Fix this bug.")
    ctx.add_assistant_message(content="I will read calculator.py.")
    ctx.add_tool_message(tool_call_id="call_1", name="read_file", content="def add(a, b): return a + b")

    messages = ctx.get_messages_for_llm()
    assert len(messages) == 4
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert messages[2].role == "assistant"
    assert messages[3].role == "tool"


def test_context_compaction():
    """Verify compaction when token limit is exceeded."""
    # Set a small token budget
    ctx = ContextManager(max_tokens=80)
    ctx.add_system_message("System prompt")
    ctx.add_user_message("Task prompt")

    # Add several verbose tool messages
    for i in range(10):
        ctx.add_assistant_message(content=f"Step {i} thought")
        ctx.add_tool_message(
            tool_call_id=f"c_{i}",
            name="read_file",
            content="A" * 500,  # very large tool output
        )

    # Initial token estimation should be high
    raw_tokens = ctx.count_tokens()
    assert raw_tokens > 200

    # Getting messages should trigger compaction
    compacted = ctx.get_messages_for_llm()
    compacted_tokens = ctx.count_tokens()

    assert compacted_tokens < raw_tokens
    # Ensure system and task prompts remain preserved at the head
    assert compacted[0].role == "system"
    assert compacted[1].role == "user"
