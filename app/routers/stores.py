"""
Space Dungeon Sweatshop - Stores Router
Store management with metrics, products, revenue, and health monitoring.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Product, Sale
from app.schemas import (
    ProductResponse,
    RevenueSummary,
    StoreHealthMetrics,
    StoreMetrics,
    StoreResponse,
)
from app.services import product_service

router = APIRouter(prefix="/stores", tags=["stores"])

# Predefined store configurations
STORES = {
    "etsy-pod": {"name": "Etsy POD Store", "platform": "Etsy + Printify"},
    "etsy-candles": {"name": "Etsy Candle Store", "platform": "Etsy"},
    "supplements": {"name": "SuppliFull Store", "platform": "SuppliFull"},
}


@router.get(
    "/",
    summary="List all stores",
    description="Get all stores with their current metrics.",
)
async def list_stores(
    db: AsyncSession = Depends(get_db),
) -> list[StoreResponse]:
    """List all stores with metrics."""
    stores: list[StoreResponse] = []

    for store_id, store_info in STORES.items():
        metrics_data = await product_service.get_store_revenue(db, store_id)

        # Get product counts
        result = await db.execute(
            select(func.count(Product.id), func.sum(Product.sales_count)).where(
                Product.store == store_id
            )
        )
        row = result.one_or_none()
        total_products = row[0] or 0
        total_sales = row[1] or 0

        # Get active product count
        result = await db.execute(
            select(func.count(Product.id)).where(
                Product.store == store_id,
                Product.status == "active",
            )
        )
        active_products = result.scalar() or 0

        avg_order = (
            round(metrics_data["total_revenue"] / total_sales, 2)
            if total_sales > 0
            else 0.0
        )

        # Calculate health score
        health_score = min(
            100.0,
            (
                (active_products / max(total_products, 1)) * 50
                + min(total_sales / 10, 50)
            ),
        )

        metrics = StoreMetrics(
            store=store_id,
            total_products=total_products,
            active_products=active_products,
            total_revenue=round(metrics_data["total_revenue"], 2),
            total_sales=total_sales,
            avg_order_value=avg_order,
            health_score=round(health_score, 1),
        )

        stores.append(
            StoreResponse(
                id=store_id,
                name=store_info["name"],
                platform=store_info["platform"],
                status="active",
                metrics=metrics,
                created_at=datetime.now(timezone.utc),
            )
        )

    return stores


@router.get(
    "/{store_id}",
    summary="Get store details",
    description="Get detailed information for a specific store.",
)
async def get_store(
    store_id: str,
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    """Get a single store by ID with metrics."""
    if store_id not in STORES:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")

    store_info = STORES[store_id]
    metrics_data = await product_service.get_store_revenue(db, store_id)

    result = await db.execute(
        select(func.count(Product.id), func.sum(Product.sales_count)).where(
            Product.store == store_id
        )
    )
    row = result.one_or_none()
    total_products = row[0] or 0
    total_sales = row[1] or 0

    result = await db.execute(
        select(func.count(Product.id)).where(
            Product.store == store_id,
            Product.status == "active",
        )
    )
    active_products = result.scalar() or 0

    avg_order = (
        round(metrics_data["total_revenue"] / total_sales, 2)
        if total_sales > 0
        else 0.0
    )

    health_score = min(
        100.0,
        (
            (active_products / max(total_products, 1)) * 50
            + min(total_sales / 10, 50)
        ),
    )

    metrics = StoreMetrics(
        store=store_id,
        total_products=total_products,
        active_products=active_products,
        total_revenue=round(metrics_data["total_revenue"], 2),
        total_sales=total_sales,
        avg_order_value=avg_order,
        health_score=round(health_score, 1),
    )

    return StoreResponse(
        id=store_id,
        name=store_info["name"],
        platform=store_info["platform"],
        status="active",
        metrics=metrics,
        created_at=datetime.now(timezone.utc),
    )


@router.get(
    "/{store_id}/products",
    response_model=list[ProductResponse],
    summary="Get store products",
    description="Get all products for a specific store.",
)
async def get_store_products(
    store_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[ProductResponse]:
    """Get all products for a store."""
    if store_id not in STORES:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")

    products = await product_service.get_store_products(db, store_id)
    return [ProductResponse.model_validate(p) for p in products]


@router.get(
    "/{store_id}/revenue",
    summary="Get store revenue",
    description="Get revenue data for a specific store.",
)
async def get_store_revenue(
    store_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get revenue data for a store."""
    if store_id not in STORES:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")

    return await product_service.get_store_revenue(db, store_id)


@router.get(
    "/{store_id}/health",
    response_model=StoreHealthMetrics,
    summary="Get store health",
    description="Get health metrics and recommendations for a store.",
)
async def get_store_health(
    store_id: str,
    db: AsyncSession = Depends(get_db),
) -> StoreHealthMetrics:
    """Get health metrics for a store."""
    if store_id not in STORES:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")

    # Get store data
    result = await db.execute(
        select(func.count(Product.id), func.sum(Product.sales_count)).where(
            Product.store == store_id
        )
    )
    row = result.one_or_none()
    total_products = row[0] or 0

    result = await db.execute(
        select(func.count(Product.id)).where(
            Product.store == store_id,
            Product.status == "active",
        )
    )
    active_products = result.scalar() or 0

    result = await db.execute(
        select(func.count(Sale.id)).where(Sale.product_id.in_(
            select(Product.id).where(Product.store == store_id)
        ))
    )
    total_sales = result.scalar() or 0

    # Calculate health score
    active_ratio = active_products / max(total_products, 1)
    health_score = min(100.0, active_ratio * 50 + min(total_sales / 10, 50))

    # Determine status
    if health_score >= 70:
        status = "healthy"
    elif health_score >= 40:
        status = "warning"
    else:
        status = "critical"

    # Build issues and recommendations
    issues: list[str] = []
    recommendations: list[str] = []

    if active_ratio < 0.5:
        issues.append(f"Only {active_products}/{total_products} products are active")
        recommendations.append("Publish more draft products to increase visibility")

    if total_sales == 0:
        issues.append("No sales recorded for this store")
        recommendations.append("Consider running promotions or adjusting pricing")

    if total_products < 5:
        issues.append("Low product count")
        recommendations.append("Generate more designs and create products")

    if not issues:
        issues.append("No critical issues detected")
        recommendations.append("Continue current strategy")

    return StoreHealthMetrics(
        store=store_id,
        health_score=round(health_score, 1),
        status=status,
        last_sync=datetime.now(timezone.utc),
        issues=issues,
        recommendations=recommendations,
    )
