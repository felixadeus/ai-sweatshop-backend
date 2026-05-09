"""
Space Dungeon Sweatshop - Sale Service
Business logic for revenue tracking and order management.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, Sale
from app.schemas import (
    OrderSyncResponse,
    RevenueSummary,
    SaleCreate,
    SaleFilterParams,
)


async def list_sales(
    db: AsyncSession,
    filters: Optional[SaleFilterParams] = None,
) -> list[Sale]:
    """
    Retrieve sales with optional filtering by platform and date range.

    Args:
        db: Async database session
        filters: Optional filter parameters

    Returns:
        List of Sale records
    """
    query = select(Sale).order_by(Sale.order_date.desc())

    if filters:
        if filters.platform:
            query = query.where(Sale.platform == filters.platform)
        if filters.date_from:
            query = query.where(Sale.order_date >= filters.date_from)
        if filters.date_to:
            query = query.where(Sale.order_date <= filters.date_to)

    result = await db.execute(query)
    return list(result.scalars().all())


async def create_sale(db: AsyncSession, data: SaleCreate) -> Sale:
    """
    Record a new sale.

    Args:
        db: Async database session
        data: Sale creation data

    Returns:
        The newly created Sale
    """
    # Auto-calculate platform fee if not provided
    fee = data.platform_fee
    if fee == 0.0:
        fee_rate = 0.065 if data.platform == "etsy" else 0.08
        fee = round(data.amount * fee_rate, 2)

    net = data.amount - fee

    sale = Sale(
        product_id=data.product_id,
        platform=data.platform,
        amount=data.amount,
        platform_fee=fee,
        net=net,
    )
    db.add(sale)
    await db.flush()
    return sale


async def get_revenue_summary(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> RevenueSummary:
    """
    Get a comprehensive revenue summary.

    Args:
        db: Async database session
        date_from: Optional start date filter
        date_to: Optional end date filter

    Returns:
        RevenueSummary with totals, breakdowns by store and period
    """
    query = select(Sale)
    if date_from:
        query = query.where(Sale.order_date >= date_from)
    if date_to:
        query = query.where(Sale.order_date <= date_to)

    result = await db.execute(query)
    sales = result.scalars().all()

    total_revenue = sum(s.amount for s in sales)
    total_fees = sum(s.platform_fee for s in sales)
    total_net = sum(s.net for s in sales)

    # By store breakdown
    result = await db.execute(select(Product.id, Product.store))
    product_stores = {row[0]: row[1] for row in result.all()}

    by_store: dict[str, dict[str, float]] = {}
    for sale in sales:
        store = product_stores.get(sale.product_id, "unknown")
        if store not in by_store:
            by_store[store] = {"revenue": 0.0, "sales": 0, "net": 0.0}
        by_store[store]["revenue"] += sale.amount
        by_store[store]["sales"] += 1
        by_store[store]["net"] += sale.net

    # By period (daily for the last 7 days, weekly otherwise)
    by_period: dict[str, float] = {}
    for sale in sales:
        period_key = sale.order_date.strftime("%Y-%m-%d")
        by_period[period_key] = by_period.get(period_key, 0.0) + sale.amount

    return RevenueSummary(
        total_revenue=round(total_revenue, 2),
        total_sales=len(sales),
        total_platform_fees=round(total_fees, 2),
        total_net=round(total_net, 2),
        by_store=by_store,
        by_period=by_period,
        period_start=date_from,
        period_end=date_to,
    )


async def sync_orders(db: AsyncSession) -> OrderSyncResponse:
    """
    Sync orders from external platforms.
    In production, this would poll Etsy and SuppliFull APIs.

    Args:
        db: Async database session

    Returns:
        OrderSyncResponse with sync results
    """
    now = datetime.now(timezone.utc)

    # Simulate fetching new orders
    result = await db.execute(select(Product).where(Product.status == "active"))
    active_products = result.scalars().all()

    if not active_products:
        return OrderSyncResponse(
            success=True,
            orders_synced=0,
            new_orders=0,
            message="No active products to sync",
            synced_at=now,
        )

    # Get current max sale ID to determine what's "new"
    result = await db.execute(func.count(Sale.id))
    before_count = result.scalar() or 0

    # Simulate finding 3-8 new orders
    import random

    new_count = random.randint(0, 5)
    for _ in range(new_count):
        product = random.choice(active_products)
        platform = "etsy" if product.store.startswith("etsy") else "supplifull"
        amount = round(random.uniform(15.0, 80.0), 2)
        fee_rate = 0.065 if platform == "etsy" else 0.08
        fee = round(amount * fee_rate, 2)

        sale = Sale(
            product_id=product.id,
            platform=platform,
            amount=amount,
            platform_fee=fee,
            net=round(amount - fee, 2),
            order_date=now,
        )
        db.add(sale)

        # Update product metrics
        product.sales_count += 1
        product.revenue += amount

    await db.flush()

    result = await db.execute(func.count(Sale.id))
    after_count = result.scalar() or 0

    return OrderSyncResponse(
        success=True,
        orders_synced=new_count,
        new_orders=new_count,
        message=f"Synced {new_count} new orders from platforms",
        synced_at=now,
    )
