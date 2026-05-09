"""
Space Dungeon Sweatshop - Research Service
Business logic for trend research and competitor analysis.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ResearchFinding, Task
from app.schemas import (
    ConceptToForgeRequest,
    ConceptToForgeResponse,
    ResearchFindingCreate,
    ResearchFindingResponse,
    ScrapeRequest,
    ScrapeResponse,
)


async def scrape_store(db: AsyncSession, data: ScrapeRequest) -> ScrapeResponse:
    """
    Scrape a competitor store for product data.
    In production, this would use a web scraper.

    Args:
        db: Async database session
        data: Scrape request with store URL

    Returns:
        ScrapeResponse with results
    """
    now = datetime.now(timezone.utc)

    # Simulate scraping — generate findings from the store
    import random

    store_name = data.store_url.split("/")[-1] if "/" in data.store_url else "unknown"
    products_found = random.randint(15, 120)

    categories = [
        "space_tshirts",
        "astronomy_posters",
        "cosmic_mugs",
        "scifi_apparel",
        "space_candles",
    ]

    # Create a research finding from the scrape
    trend_score = round(random.uniform(60.0, 95.0), 1)
    finding = ResearchFinding(
        competitor_store=store_name,
        product_category=random.choice(categories),
        trend_score=trend_score,
        estimated_sales=random.randint(200, 3000),
        concept_extracted=f"Trending {random.choice(categories)} from {store_name}",
        sent_to_forge=False,
        created_at=now,
    )
    db.add(finding)
    await db.flush()

    return ScrapeResponse(
        success=True,
        store_url=data.store_url,
        products_found=products_found,
        message=f"Scraped {products_found} products from {store_name}",
        scraped_at=now,
    )


async def get_trending_designs(db: AsyncSession, limit: int = 10) -> list[ResearchFinding]:
    """
    Get the most trending research findings.

    Args:
        db: Async database session
        limit: Maximum number of results

    Returns:
        List of ResearchFinding records sorted by trend score
    """
    result = await db.execute(
        select(ResearchFinding)
        .order_by(ResearchFinding.trend_score.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_competitors(db: AsyncSession) -> list[dict]:
    """
    Get a list of tracked competitor stores with aggregated metrics.

    Args:
        db: Async database session

    Returns:
        List of competitor summary dictionaries
    """
    result = await db.execute(
        select(
            ResearchFinding.competitor_store,
            func.count(ResearchFinding.id),
            func.avg(ResearchFinding.trend_score),
            func.sum(ResearchFinding.estimated_sales),
        ).group_by(ResearchFinding.competitor_store)
    )

    competitors = []
    for row in result.all():
        competitors.append(
            {
                "store": row[0],
                "findings_count": row[1],
                "avg_trend_score": round(row[2] or 0, 1),
                "total_estimated_sales": row[3] or 0,
            }
        )

    return competitors


async def get_ai_news(db: AsyncSession) -> list[dict]:
    """
    Get the latest AI news relevant to the business.
    In production, this would call a news API.

    Args:
        db: Async database session

    Returns:
        List of news article dictionaries
    """
    # Simulated AI news feed
    now = datetime.now(timezone.utc)
    return [
        {
            "title": "Stable Diffusion 3.5 Released: Faster Image Generation",
            "source": "AI Tech Daily",
            "summary": "New model promises 2x faster inference with higher quality outputs for product designs.",
            "url": "https://example.com/sd35",
            "published_at": (now - timedelta(hours=2)).isoformat(),
            "relevance": "high",
        },
        {
            "title": "Etsy Updates API with New Webhook Support",
            "source": "Etsy Developer Blog",
            "summary": "Real-time order notifications now available through webhooks, reducing sync delays.",
            "url": "https://example.com/etsy-webhooks",
            "published_at": (now - timedelta(hours=5)).isoformat(),
            "relevance": "high",
        },
        {
            "title": "Printify Introduces UV Printing for Premium Products",
            "source": "Printify News",
            "summary": "New printing technology enables higher quality designs on select product types.",
            "url": "https://example.com/printify-uv",
            "published_at": (now - timedelta(hours=8)).isoformat(),
            "relevance": "medium",
        },
        {
            "title": "AI Art Trends: Cosmic Themes Dominate Q1 2025",
            "source": "Design Trends Weekly",
            "summary": "Space and cosmic themed designs see 340% increase in consumer demand.",
            "url": "https://example.com/cosmic-trends",
            "published_at": (now - timedelta(hours=12)).isoformat(),
            "relevance": "high",
        },
        {
            "title": "SuppliFull Adds New Vitamin Line for Dropshipping",
            "source": "SuppliFull Blog",
            "summary": "Expanded catalog includes 12 new supplement SKUs with US fulfillment.",
            "url": "https://example.com/supplifull-vitamins",
            "published_at": (now - timedelta(hours=18)).isoformat(),
            "relevance": "medium",
        },
    ]


async def send_concept_to_forge(
    db: AsyncSession, data: ConceptToForgeRequest
) -> ConceptToForgeResponse:
    """
    Send a research concept to Forge for design generation.
    Creates a design task and updates the research finding.

    Args:
        db: Async database session
        data: Concept to forge request

    Returns:
        ConceptToForgeResponse with the created task
    """
    now = datetime.now(timezone.utc)

    # Create a design task for Forge
    task = Task(
        agent_id="Forge",
        type="design",
        status="pending",
        payload={
            "concept": data.concept,
            "product_type": data.product_type,
            "priority": data.priority,
            "source": "nova_research",
        },
        priority=data.priority,
        created_at=now,
    )
    db.add(task)
    await db.flush()

    # Create a research finding record for this concept
    finding = ResearchFinding(
        competitor_store="manual_submission",
        product_category=f"{data.product_type}_design",
        trend_score=0.0,
        estimated_sales=0,
        concept_extracted=data.concept,
        sent_to_forge=True,
        forge_design_id=None,
        created_at=now,
    )
    db.add(finding)
    await db.flush()

    return ConceptToForgeResponse(
        success=True,
        concept=data.concept,
        task_id=task.id,
        message=f"Concept sent to Forge as task #{task.id}",
        sent_at=now,
    )


async def list_findings(db: AsyncSession, limit: int = 50) -> list[ResearchFinding]:
    """
    Get all research findings.

    Args:
        db: Async database session
        limit: Maximum number of results

    Returns:
        List of ResearchFinding records
    """
    result = await db.execute(
        select(ResearchFinding)
        .order_by(ResearchFinding.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_finding(
    db: AsyncSession, data: ResearchFindingCreate
) -> ResearchFinding:
    """
    Create a new research finding directly.

    Args:
        db: Async database session
        data: Research finding creation data

    Returns:
        The newly created ResearchFinding
    """
    finding = ResearchFinding(
        competitor_store=data.competitor_store,
        product_category=data.product_category,
        trend_score=data.trend_score,
        estimated_sales=data.estimated_sales,
        concept_extracted=data.concept_extracted,
        sent_to_forge=False,
    )
    db.add(finding)
    await db.flush()
    return finding
