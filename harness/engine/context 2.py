"""Context window and message history manager with token budgeting and compaction."""

import logging
from typing import Any, Dict, List, Optional
from harness.config import settings
from harness.llm.base import ChatMessage
from harness.llm.token_counter import estimate_messages_tokens, estimate_tokens

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages conversational history, token budgets, task isolation, and dynamic message compaction."""

    def __init__(self, task_id: str = "default_task", max_tokens: Optional[int] = None):
        self.task_id = task_id
        self.max_tokens = max_tokens or settings.harness_max_context_tokens
        self._messages: List[ChatMessage] = []

    @property
    def messages(self) -> List[ChatMessage]:
        return self._messages

    def add_system_message(self, content: str) -> None:
        self._messages.append(ChatMessage(role="system", content=content))

    def add_user_message(self, content: str) -> None:
        self._messages.append(ChatMessage(role="user", content=content))

    def add_assistant_message(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self._messages.append(
            ChatMessage(role="assistant", content=content, tool_calls=tool_calls)
        )

    def add_tool_message(
        self, tool_call_id: str, name: str, content: str
    ) -> None:
        self._messages.append(
            ChatMessage(
                role="tool",
                name=name,
                tool_call_id=tool_call_id,
                content=content,
            )
        )

    def count_tokens(self) -> int:
        """Calculates total estimated tokens in the message context."""
        return estimate_messages_tokens(self._messages)

    def compact(self, force: bool = False) -> bool:
        """Prunes and compacts older messages when approaching the token limit.

        Preserves system prompt, original task instructions, recent history, and critical error/verification evidence.
        """
        current_tokens = self.count_tokens()
        if not force and current_tokens <= self.max_tokens:
            return False

        logger.info(
            f"[{self.task_id}] Context token budget compaction triggered ({current_tokens} > {self.max_tokens})."
        )

        if len(self._messages) <= 4:
            return False

        # Phase 1: Truncate large tool output messages in historical turns (excluding system, initial user, and last 4 messages)
        for i in range(2, len(self._messages) - 4):
            msg = self._messages[i]
            if msg.role == "tool" and msg.content and len(msg.content) > 300:
                # Do not truncate if message contains critical test verification evidence or errors
                is_critical_evidence = any(
                    kw in msg.content.lower() for kw in ("verification", "test failure", "failed:", "error:", "traceback")
                )
                if not is_critical_evidence:
                    msg.content = (
                        msg.content[:150]
                        + f"\n... [Tool '{msg.name or 'tool'}' output compacted to save tokens] ...\n"
                        + msg.content[-80:]
                    )

        current_tokens = self.count_tokens()
        if not force and current_tokens <= self.max_tokens:
            return True

        # Phase 2: Compact middle message turns into a structured summary
        head = self._messages[:2]
        tail = self._messages[-4:]

        # Extract actions taken in middle history
        middle_actions = []
        for msg in self._messages[2:-4]:
            if msg.role == "tool" and msg.name:
                middle_actions.append(msg.name)
            elif msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    fname = tc.get("function", {}).get("name") or tc.get("name")
                    if fname:
                        middle_actions.append(str(fname))

        actions_summary = ", ".join(sorted(set(middle_actions))) if middle_actions else "file exploration and edits"
        summary_text = (
            f"[Context Compaction Note for task '{self.task_id}']: "
            f"Prior turns were summarized to conserve context tokens. Key tools executed earlier: [{actions_summary}]. "
            "Original instructions, critical errors, and active steps are preserved."
        )

        summary_msg = ChatMessage(role="user", content=summary_text)
        self._messages = head + [summary_msg] + tail

        logger.info(f"[{self.task_id}] Context compacted to {self.count_tokens()} tokens.")
        return True

    def get_messages_for_llm(self) -> List[ChatMessage]:
        """Returns the bounded and compacted message list for the LLM call."""
        self.compact()
        return self._messages
