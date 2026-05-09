"""
Space Dungeon Sweatshop - Sales Router
Revenue tracking, order management, and platform syncing.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    OrderSyncResponse,
    RevenueSummary,
    SaleCreate,
    SaleFilterParams,
    SaleResponse,
)
from app.services import sale_service
from app.websocket import manager

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get(
    "/",
    response_model=list[SaleResponse],
    summary="List sales",
    description="Retrieve all sales with optional filters for platform and date range.",
)
async def list_sales(
    platform: str | None = Query(None, description="Filter by platform (etsy/supplifull)"),
    date_from: datetime | None = Query(None, description="Filter from date"),
    date_to: datetime | None = Query(None, description="Filter to date"),
    db: AsyncSession = Depends(get_db),
) -> list[SaleResponse]:
    """List sales with optional filtering."""
    filters = SaleFilterParams(platform=platform, date_from=date_from, date_to=date_to)
    sales = await sale_service.list_sales(db, filters)
    return [SaleResponse.model_validate(s) for s in sales]


@router.post(
    "/",
    response_model=SaleResponse,
    status_code=201,
    summary="Record sale",
    description="Record a new sale/transaction.",
)
async def create_sale(
    data: SaleCreate,
    db: AsyncSession = Depends(get_db),
) -> SaleResponse:
    """Record a new sale."""
    sale = await sale_service.create_sale(db, data)

    # Broadcast to WebSocket
    await manager.broadcast(
        "sales",
        "sale.new",
        "system",
        {
            "sale_id": sale.id,
            "product_id": sale.product_id,
            "amount": sale.amount,
            "platform": sale.platform,
        },
    )

    return SaleResponse.model_validate(sale)


@router.get(
    "/revenue",
    response_model=RevenueSummary,
    summary="Get revenue summary",
    description="Get a comprehensive revenue summary with breakdowns by store and period.",
)
async def get_revenue_summary(
    date_from: datetime | None = Query(None, description="Start date for revenue calculation"),
    date_to: datetime | None = Query(None, description="End date for revenue calculation"),
    db: AsyncSession = Depends(get_db),
) -> RevenueSummary:
    """Get the revenue summary."""
    return await sale_service.get_revenue_summary(db, date_from, date_to)


@router.get(
    "/orders",
    response_model=list[SaleResponse],
    summary="List orders",
    description="Get a list of all orders (alias for /sales).",
)
async def list_orders(
    db: AsyncSession = Depends(get_db),
) -> list[SaleResponse]:
    """List all orders."""
    sales = await sale_service.list_sales(db)
    return [SaleResponse.model_validate(s) for s in sales]


@router.post(
    "/orders/sync",
    response_model=OrderSyncResponse,
    summary="Sync orders",
    description="Sync orders from external platforms (Etsy, SuppliFull).",
)
async def sync_orders(
    db: AsyncSession = Depends(get_db),
) -> OrderSyncResponse:
    """Sync orders from external platforms."""
    result = await sale_service.sync_orders(db)

    if result.new_orders > 0:
        await manager.broadcast(
            "sales",
            "orders.synced",
            "Minions",
            {
                "orders_synced": result.orders_synced,
                "new_orders": result.new_orders,
            },
        )

    return result
