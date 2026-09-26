"""Endpoints for retrieving structured logs and execution telemetry."""

from fastapi import APIRouter, HTTPException
from harness.api.schemas.log_models import LogsResponse
from harness.telemetry.logger import telemetry_bus

router = APIRouter(prefix="/api/v1/tasks", tags=["Telemetry & Logs"])


@router.get("/{task_id}/logs", response_model=LogsResponse)
async def get_task_logs(task_id: str):
    """Retrieves all structured telemetry events for a specific task."""
    events = telemetry_bus.get_events(task_id)
    return LogsResponse(
        task_id=task_id,
        events_count=len(events),
        events=events,
    )
