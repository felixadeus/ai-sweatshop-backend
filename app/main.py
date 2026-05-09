"""
Space Dungeon Sweatshop - FastAPI Application Entry Point
Complete API server for the AI agent command center.
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import engine
from app.models import Base
from app.routers import (
    agents,
    designs,
    etsy,
    etsy_oauth,
    products,
    research,
    sales,
    stores,
    tasks,
    websocket as ws_router,
)
from app.schemas import HealthCheckResponse, SystemStats
from app.seed import seed_all

# ─── Logging Configuration ─────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Application State ─────────────────────────────────────

_start_time = time.time()


# ─── Lifespan Manager ──────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Creates database tables and seeds data on startup.
    """
    logger.info("Starting Space Dungeon Sweatshop API...")

    # Create all database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Seed with realistic data
    await seed_all()
    logger.info("Database seeded")

    yield

    # Shutdown
    logger.info("Shutting down API...")
    await engine.dispose()


# ─── FastAPI App Instance ──────────────────────────────────

app = FastAPI(
    title="Space Dungeon Sweatshop API",
    description=(
        "AI Agent Command Center for managing e-commerce businesses. "
        "Controls Ultron (overseer), Forge (designer), Nova (researcher), "
        "and Minions (workers) across Etsy POD, candle, and supplement stores."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS Middleware ───────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for frontend integration
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Exception Handler ─────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


# ─── Health Check ──────────────────────────────────────────

@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["health"],
    summary="Health check",
    description="Check API health and get basic system status.",
)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint for monitoring."""
    from app.database import AsyncSessionLocal
    from app.models import Agent, Task
    from sqlalchemy import func, select

    uptime = time.time() - _start_time
    agents_online = 0
    tasks_pending = 0

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.count(Agent.id)).where(Agent.status != "alert")
            )
            agents_online = result.scalar() or 0

            result = await session.execute(
                select(func.count(Task.id)).where(Task.status == "pending")
            )
            tasks_pending = result.scalar() or 0
    except Exception as e:
        logger.warning(f"Health check DB query failed: {e}")

    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        uptime_seconds=round(uptime, 2),
        agents_online=agents_online,
        tasks_pending=tasks_pending,
        timestamp=datetime.now(timezone.utc),
    )


# ─── System Stats ──────────────────────────────────────────

@app.get(
    "/stats",
    response_model=SystemStats,
    tags=["system"],
    summary="System statistics",
    description="Get comprehensive system statistics across all modules.",
)
async def get_system_stats() -> SystemStats:
    """Get overall system statistics."""
    from app.database import AsyncSessionLocal
    from app.models import Agent, Design, Product, ResearchFinding, Sale, Task
    from sqlalchemy import func, select

    stats = {
        "total_agents": 0,
        "agents_working": 0,
        "agents_idle": 0,
        "agents_alert": 0,
        "total_tasks": 0,
        "tasks_pending": 0,
        "tasks_running": 0,
        "tasks_completed": 0,
        "tasks_failed": 0,
        "total_products": 0,
        "products_active": 0,
        "total_sales": 0,
        "total_revenue": 0.0,
        "total_designs": 0,
        "designs_draft": 0,
        "designs_approved": 0,
        "research_findings": 0,
    }

    try:
        async with AsyncSessionLocal() as session:
            # Agent stats
            result = await session.execute(select(func.count(Agent.id)))
            stats["total_agents"] = result.scalar() or 0

            for status in ["working", "idle", "alert"]:
                result = await session.execute(
                    select(func.count(Agent.id)).where(Agent.status == status)
                )
                stats[f"agents_{status}"] = result.scalar() or 0

            # Task stats
            result = await session.execute(select(func.count(Task.id)))
            stats["total_tasks"] = result.scalar() or 0

            for status in ["pending", "running", "completed", "failed"]:
                result = await session.execute(
                    select(func.count(Task.id)).where(Task.status == status)
                )
                stats[f"tasks_{status}"] = result.scalar() or 0

            # Product stats
            result = await session.execute(select(func.count(Product.id)))
            stats["total_products"] = result.scalar() or 0

            result = await session.execute(
                select(func.count(Product.id)).where(Product.status == "active")
            )
            stats["products_active"] = result.scalar() or 0

            # Sales stats
            result = await session.execute(select(func.count(Sale.id)))
            stats["total_sales"] = result.scalar() or 0

            result = await session.execute(select(func.sum(Sale.amount)))
            stats["total_revenue"] = float(result.scalar() or 0)

            # Design stats
            result = await session.execute(select(func.count(Design.id)))
            stats["total_designs"] = result.scalar() or 0

            for status in ["draft", "approved"]:
                result = await session.execute(
                    select(func.count(Design.id)).where(Design.status == status)
                )
                stats[f"designs_{status}"] = result.scalar() or 0

            # Research stats
            result = await session.execute(select(func.count(ResearchFinding.id)))
            stats["research_findings"] = result.scalar() or 0

    except Exception as e:
        logger.warning(f"Stats DB query failed: {e}")

    return SystemStats(
        total_agents=stats["total_agents"],
        agents_working=stats["agents_working"],
        agents_idle=stats["agents_idle"],
        agents_alert=stats["agents_alert"],
        total_tasks=stats["total_tasks"],
        tasks_pending=stats["tasks_pending"],
        tasks_running=stats["tasks_running"],
        tasks_completed=stats["tasks_completed"],
        tasks_failed=stats["tasks_failed"],
        total_products=stats["total_products"],
        products_active=stats["products_active"],
        total_sales=stats["total_sales"],
        total_revenue=round(stats["total_revenue"], 2),
        total_designs=stats["total_designs"],
        designs_draft=stats["designs_draft"],
        designs_approved=stats["designs_approved"],
        research_findings=stats["research_findings"],
        timestamp=datetime.now(timezone.utc),
    )


# ═══════════════════════════════════════════════════════════
# Include Routers
# ═══════════════════════════════════════════════════════════

app.include_router(agents.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(designs.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(sales.router, prefix="/api")
app.include_router(research.router, prefix="/api")
app.include_router(stores.router, prefix="/api")
app.include_router(etsy.router, prefix="/api")
app.include_router(etsy_oauth.router, prefix="/api")
app.include_router(ws_router.router)


# ─── Static Frontend ───────────────────────────────────────
# Mount the built React frontend at root

_DIST = Path(__file__).resolve().parent.parent / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")
    app.mount("/public", StaticFiles(directory=str(_DIST)), name="public")

    @app.get("/", tags=["root"], summary="Frontend")
    async def serve_index():
        """Serve the React SPA index.html."""
        return FileResponse(str(_DIST / "index.html"))

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str):
        """SPA catch-all: serve index.html for all non-API routes."""
        if path.startswith(("api/", "ws/", "docs", "redoc", "health", "stats", "openapi.json")):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        # Check for static files first
        file_path = _DIST / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_DIST / "index.html"))
else:
    # ─── Root Endpoint (API only mode) ─────────────────────
    @app.get("/", tags=["root"], summary="API root")
    async def root() -> dict:
        """Root endpoint with API info."""
        return {
            "name": "Space Dungeon Sweatshop API",
            "version": "1.0.0",
            "description": "AI Agent Command Center for e-commerce management",
            "docs": "/docs",
            "endpoints": {
                "agents": "/api/agents",
                "tasks": "/api/tasks",
                "designs": "/api/designs",
                "products": "/api/products",
                "sales": "/api/sales",
                "research": "/api/research",
                "stores": "/api/stores",
                "websocket": "/ws/{channel}",
                "health": "/health",
                "stats": "/stats",
            },
        }
