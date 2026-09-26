"""Structured JSON event logger and in-memory event stream."""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


import re

SECRET_REDACTION_PATTERNS = [
    (r"(?i)(api[_-]?key|key|secret|token|password|auth|bearer)[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9_\-\.\:\~]+)[\"']?", r"\1: [REDACTED]"),
    (r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_OPENAI_KEY]"),
    (r"ghp_[a-zA-Z0-9]{20,}", "[REDACTED_GITHUB_TOKEN]"),
]


def redact_secrets(data: Any) -> Any:
    """Recursively redacts API keys, credentials, and tokens from telemetry payloads."""
    if isinstance(data, str):
        redacted = data
        for pattern, replacement in SECRET_REDACTION_PATTERNS:
            redacted = re.sub(pattern, replacement, redacted)
        return redacted
    elif isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if any(s in k.lower() for s in ("api_key", "secret", "password", "token", "auth")):
                new_dict[k] = "[REDACTED]"
            else:
                new_dict[k] = redact_secrets(v)
        return new_dict
    elif isinstance(data, list):
        return [redact_secrets(item) for item in data]
    return data


class TelemetryEvent(BaseModel):
    """Structured telemetry event model with secret redaction."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    task_id: str
    event_type: str
    stage: str = "UNKNOWN"
    step_number: Optional[int] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""

    def to_json(self) -> str:
        d = self.model_dump()
        d["data"] = redact_secrets(d["data"])
        d["message"] = redact_secrets(d["message"])
        return json.dumps(d)


class TelemetryBus:
    """In-memory and file-backed event bus that captures, redacts, and buffers structured execution traces."""

    def __init__(self, persistence_dir: Optional[str] = ".harness_reports"):
        self._events_by_task: Dict[str, List[TelemetryEvent]] = {}
        self.persistence_dir = persistence_dir

    def emit(
        self,
        task_id: str,
        event_type: str,
        message: str = "",
        stage: str = "UNKNOWN",
        step_number: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> TelemetryEvent:
        safe_message = redact_secrets(message)
        safe_data = redact_secrets(data or {})

        event = TelemetryEvent(
            task_id=task_id,
            event_type=event_type,
            stage=stage,
            step_number=step_number,
            data=safe_data,
            message=safe_message,
        )
        if task_id not in self._events_by_task:
            self._events_by_task[task_id] = []
        self._events_by_task[task_id].append(event)
        
        # Persist event to jsonl trace file if persistence directory is configured
        if self.persistence_dir:
            try:
                import os
                os.makedirs(self.persistence_dir, exist_ok=True)
                trace_file = os.path.join(self.persistence_dir, f"{task_id}_telemetry.jsonl")
                with open(trace_file, "a", encoding="utf-8") as f:
                    f.write(event.to_json() + "\n")
            except Exception as e:
                logger.debug(f"Failed to persist telemetry event to disk: {e}")

        logger.debug(f"[Telemetry:{task_id}] {event_type} - {safe_message}")
        return event

    def get_events(self, task_id: str) -> List[TelemetryEvent]:
        events = self._events_by_task.get(task_id, [])
        if not events and self.persistence_dir:
            try:
                import os
                trace_file = os.path.join(self.persistence_dir, f"{task_id}_telemetry.jsonl")
                if os.path.exists(trace_file):
                    events = []
                    with open(trace_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                events.append(TelemetryEvent.model_validate_json(line.strip()))
                    self._events_by_task[task_id] = events
            except Exception as e:
                logger.debug(f"Failed to load persisted events for {task_id}: {e}")
        return events

    def clear(self, task_id: Optional[str] = None) -> None:
        if task_id:
            self._events_by_task.pop(task_id, None)
        else:
            self._events_by_task.clear()


# Global telemetry bus singleton
telemetry_bus = TelemetryBus()
