"""Health and readiness check endpoints for backend monitoring."""

from datetime import datetime, timezone
from fastapi import APIRouter
from harness import __version__
from harness.config import settings

router = APIRouter(tags=["Health & Readiness"])


@router.get("/health")
@router.get("/api/v1/health")
async def health_check():
    """Liveness probe returning server status and configuration summary."""
    return {
        "status": "ok",
        "service": "ai-coding-harness",
        "version": __version__,
        "configured_model": settings.ai_model,
        "has_api_key": settings.has_valid_api_key,
        "max_steps": settings.harness_max_steps,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
@router.get("/api/v1/ready")
async def readiness_check():
    """Readiness probe indicating if the harness is initialized and accepting tasks."""
    return {
        "status": "ready",
        "service": "ai-coding-harness",
        "version": __version__,
        "ready": True,
        "host": settings.harness_host,
        "port": settings.harness_port,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
