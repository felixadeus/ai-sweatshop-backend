"""
Space Dungeon Sweatshop - Products Router
Product management across stores with publishing capabilities.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ProductCreate,
    ProductFilterParams,
    ProductPublishResponse,
    ProductResponse,
    ProductUpdate,
)
from app.services import product_service
from app.websocket import manager

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "/",
    response_model=list[ProductResponse],
    summary="List all products",
    description="Retrieve all products with optional filters for store and status.",
)
async def list_products(
    store: str | None = Query(None, description="Filter by store (etsy-pod/etsy-candles/supplements)"),
    status: str | None = Query(None, description="Filter by status (draft/active/paused)"),
    db: AsyncSession = Depends(get_db),
) -> list[ProductResponse]:
    """List products with optional filtering."""
    filters = ProductFilterParams(store=store, status=status)
    products = await product_service.list_products(db, filters)
    return [ProductResponse.model_validate(p) for p in products]


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=201,
    summary="Create product",
    description="Create a new product from a design or from scratch.",
)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Create a new product."""
    product = await product_service.create_product(db, data)

    # Broadcast to WebSocket
    await manager.broadcast(
        "tasks",
        "product.created",
        "Minions",
        {
            "product_id": product.id,
            "title": product.title,
            "store": product.store,
            "status": product.status,
        },
    )

    return ProductResponse.model_validate(product)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product details",
    description="Get detailed information for a specific product.",
)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Get a single product by ID."""
    product = await product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return ProductResponse.model_validate(product)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update product",
    description="Update a product's price, status, description, or other properties.",
)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Update a product's properties."""
    product = await product_service.update_product(db, product_id, data)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    # Broadcast update if status changed
    if data.status:
        await manager.broadcast(
            "tasks",
            f"product.{data.status}",
            "Minions",
            {"product_id": product_id, "status": product.status},
        )

    return ProductResponse.model_validate(product)


@router.post(
    "/{product_id}/publish",
    response_model=ProductPublishResponse,
    summary="Publish product",
    description="Publish a product to its target store (Etsy or SuppliFull).",
)
async def publish_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> ProductPublishResponse:
    """Publish a product to its store."""
    result = await product_service.publish_product(db, product_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    if result.success:
        await manager.broadcast(
            "tasks",
            "product.published",
            "Minions",
            {
                "product_id": product_id,
                "etsy_listing_id": result.etsy_listing_id,
            },
        )

    return result


@router.delete(
    "/{product_id}",
    status_code=204,
    summary="Delete product",
    description="Remove a product from the system.",
)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a product by ID."""
    deleted = await product_service.delete_product(db, product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
