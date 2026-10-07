"""FastAPI application composition and browser asset delivery."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import close_database, initialize_database
from app.exceptions import register_exception_handlers
from app.routes_auth import router as auth_router
from app.routes_tasks import router as tasks_router
from app.schemas import SuccessResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    logger.info("application_started")
    yield
    close_database()
    logger.info("application_stopped")


app = FastAPI(
    title="Task Manager API",
    version="1.0.0",
    description="JWT-protected task management API with owner-scoped tasks.",
    lifespan=lifespan,
)
register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(tasks_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health", response_model=SuccessResponse[dict[str, str]], tags=["health"])
def health() -> SuccessResponse[dict[str, str]]:
    """Return an unauthenticated deployment health probe."""
    return SuccessResponse(message="Service is healthy.", data={"status": "healthy"})


@app.get("/", include_in_schema=False)
def browser_index() -> FileResponse:
    """Serve the browser application shell."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{browser_path:path}", include_in_schema=False)
def browser_fallback(browser_path: str) -> FileResponse:
    """Serve SPA browser routes without swallowing API 404 responses."""
    if browser_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(STATIC_DIR / "index.html")
