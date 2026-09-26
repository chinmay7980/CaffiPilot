"""FastAPI application factory and server startup."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from harness import __version__
from harness.api.routes.health import router as health_router
from harness.api.routes.logs import router as logs_router
from harness.api.routes.tasks import router as tasks_router
from harness.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.harness_log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("harness")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    logger.info(f"AI Coding Harness v{__version__} booting up...")
    logger.info(f"Configured Model: {settings.ai_model}")
    logger.info(f"API Key Present: {settings.has_valid_api_key}")
    yield
    logger.info("AI Coding Harness shutting down...")


app = FastAPI(
    title="AI Coding Harness API",
    description="Autonomous Software Engineering Agent Harness for LCC × DevClub Hackathon 2026",
    version=__version__,
    lifespan=lifespan,
)

# Enable CORS for local dashboards or frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(logs_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "harness.api.server:app",
        host=settings.harness_host,
        port=settings.harness_port,
        reload=True,
    )
