"""
Space Dungeon Sweatshop - Product Service
Business logic for product management across stores.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, Sale
from app.schemas import (
    ProductCreate,
    ProductFilterParams,
    ProductPublishResponse,
    ProductUpdate,
)


async def list_products(
    db: AsyncSession,
    filters: Optional[ProductFilterParams] = None,
) -> list[Product]:
    """
    Retrieve products with optional filtering by store and status.

    Args:
        db: Async database session
        filters: Optional filter parameters

    Returns:
        List of Product records
    """
    query = select(Product).order_by(Product.created_at.desc())

    if filters:
        if filters.store:
            query = query.where(Product.store == filters.store)
        if filters.status:
            query = query.where(Product.status == filters.status)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_product(db: AsyncSession, product_id: int) -> Optional[Product]:
    """
    Retrieve a single product by ID.

    Args:
        db: Async database session
        product_id: The product's primary key

    Returns:
        The Product record, or None if not found
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def create_product(db: AsyncSession, data: ProductCreate) -> Product:
    """
    Create a new product from a design or scratch.

    Args:
        db: Async database session
        data: Product creation data

    Returns:
        The newly created Product
    """
    product = Product(
        design_id=data.design_id,
        store=data.store,
        title=data.title,
        description=data.description,
        price=data.price,
        cost=data.cost,
        printify_product_id=data.printify_product_id,
        etsy_listing_id=data.etsy_listing_id,
        supplifull_sku=data.supplifull_sku,
        status="draft",
    )
    db.add(product)
    await db.flush()
    return product


async def update_product(
    db: AsyncSession, product_id: int, data: ProductUpdate
) -> Optional[Product]:
    """
    Update a product's properties.

    Args:
        db: Async database session
        product_id: The product's primary key
        data: Update data

    Returns:
        The updated Product, or None if not found
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.flush()
    return product


async def publish_product(
    db: AsyncSession, product_id: int
) -> Optional[ProductPublishResponse]:
    """
    Publish a product to its target store.
    In production, this would call Etsy/Printify APIs.

    Args:
        db: Async database session
        product_id: The product's primary key

    Returns:
        Publish response, or None if not found
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        return None

    if product.status == "active":
        return ProductPublishResponse(
            success=False,
            product_id=product_id,
            etsy_listing_id=product.etsy_listing_id,
            message="Product is already active",
            published_at=datetime.now(timezone.utc),
        )

    # Simulate publishing — assign mock listing IDs
    now = datetime.now(timezone.utc)
    product.status = "active"

    if product.store.startswith("etsy") and not product.etsy_listing_id:
        product.etsy_listing_id = f"ETSY-LST-{product.id + 10000}"
    elif product.store == "supplements" and not product.supplifull_sku:
        product.supplifull_sku = f"SUP-{product.id + 5000}"

    await db.flush()

    return ProductPublishResponse(
        success=True,
        product_id=product_id,
        etsy_listing_id=product.etsy_listing_id,
        message=f"Product published to {product.store}",
        published_at=now,
    )


async def get_store_products(db: AsyncSession, store_id: str) -> list[Product]:
    """
    Get all products for a specific store.

    Args:
        db: Async database session
        store_id: The store identifier

    Returns:
        List of Product records for this store
    """
    result = await db.execute(
        select(Product)
        .where(Product.store == store_id)
        .order_by(Product.created_at.desc())
    )
    return list(result.scalars().all())


async def get_store_revenue(db: AsyncSession, store_id: str) -> dict:
    """
    Get revenue summary for a specific store.

    Args:
        db: Async database session
        store_id: The store identifier

    Returns:
        Dictionary with revenue metrics
    """
    result = await db.execute(
        select(Product).where(
            Product.store == store_id,
            Product.status == "active",
        )
    )
    products = result.scalars().all()
    product_ids = [p.id for p in products]

    if not product_ids:
        return {
            "store": store_id,
            "total_revenue": 0.0,
            "total_sales": 0,
            "product_count": 0,
        }

    result = await db.execute(
        select(func.count(Sale.id), func.sum(Sale.amount), func.sum(Sale.net)).where(
            Sale.product_id.in_(product_ids)
        )
    )
    row = result.one_or_none()

    return {
        "store": store_id,
        "total_revenue": float(row[1] or 0),
        "total_sales": row[0] or 0,
        "total_net": float(row[2] or 0),
        "product_count": len(product_ids),
    }


async def delete_product(db: AsyncSession, product_id: int) -> bool:
    """
    Delete a product by ID.

    Args:
        db: Async database session
        product_id: The product's primary key

    Returns:
        True if deleted, False if not found
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        return False

    await db.delete(product)
    await db.flush()
    return True
