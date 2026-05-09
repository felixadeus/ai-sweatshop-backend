"""
Space Dungeon Sweatshop - Research Router
Competitor scraping, trend analysis, and concept-to-forge pipeline.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ConceptToForgeRequest,
    ConceptToForgeResponse,
    ResearchFindingResponse,
    ScrapeRequest,
    ScrapeResponse,
)
from app.services import research_service
from app.websocket import manager

router = APIRouter(prefix="/research", tags=["research"])


@router.post(
    "/scrape",
    response_model=ScrapeResponse,
    summary="Scrape competitor store",
    description="Scrape a competitor Etsy store for product and trend data.",
)
async def scrape_store(
    data: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
) -> ScrapeResponse:
    """Scrape a competitor store."""
    result = await research_service.scrape_store(db, data)

    # Broadcast to WebSocket
    await manager.broadcast(
        "tasks",
        "research.scraped",
        "Nova",
        {
            "store_url": data.store_url,
            "products_found": result.products_found,
        },
    )

    return result


@router.get(
    "/trends",
    response_model=list[ResearchFindingResponse],
    summary="Get trending designs",
    description="Get the highest-trending research findings sorted by trend score.",
)
async def get_trending_designs(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> list[ResearchFindingResponse]:
    """Get trending research findings."""
    findings = await research_service.get_trending_designs(db, limit)
    return [ResearchFindingResponse.model_validate(f) for f in findings]


@router.get(
    "/competitors",
    summary="List tracked competitors",
    description="Get a list of all tracked competitor stores with aggregated metrics.",
)
async def list_competitors(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get tracked competitor stores."""
    return await research_service.list_competitors(db)


@router.get(
    "/news",
    summary="Get AI news",
    description="Get the latest AI news relevant to the business.",
)
async def get_ai_news(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get AI news feed."""
    return await research_service.get_ai_news(db)


@router.get(
    "/findings",
    response_model=list[ResearchFindingResponse],
    summary="List research findings",
    description="Get all research findings.",
)
async def list_findings(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[ResearchFindingResponse]:
    """List all research findings."""
    findings = await research_service.list_findings(db, limit)
    return [ResearchFindingResponse.model_validate(f) for f in findings]


@router.post(
    "/concept-to-forge",
    response_model=ConceptToForgeResponse,
    summary="Send concept to Forge",
    description="Send a research concept to Forge for design generation.",
)
async def send_concept_to_forge(
    data: ConceptToForgeRequest,
    db: AsyncSession = Depends(get_db),
) -> ConceptToForgeResponse:
    """Send a concept to Forge for design."""
    result = await research_service.send_concept_to_forge(db, data)

    # Broadcast pipeline event
    await manager.broadcast(
        "tasks",
        "pipeline.research_to_forge",
        "Nova",
        {
            "concept": data.concept,
            "task_id": result.task_id,
            "product_type": data.product_type,
        },
    )

    return result
