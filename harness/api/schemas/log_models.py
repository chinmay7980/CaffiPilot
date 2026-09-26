"""FastAPI schemas for structured logs and telemetry."""

from typing import List
from pydantic import BaseModel
from harness.telemetry.logger import TelemetryEvent


class LogsResponse(BaseModel):
    """Container for streamed or queried telemetry events."""

    task_id: str
    events_count: int
    events: List[TelemetryEvent]
