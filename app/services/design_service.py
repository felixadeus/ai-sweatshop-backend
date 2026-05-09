"""
Space Dungeon Sweatshop - Design Service
Business logic for design generation and gallery management.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Design
from app.schemas import (
    DesignApprovalResponse,
    DesignCreate,
    DesignFilterParams,
    DesignGenerateRequest,
    DesignUpdate,
)


async def generate_design(db: AsyncSession, data: DesignGenerateRequest) -> Design:
    """
    Generate a new design from a prompt.
    In production, this would call an image generation API.

    Args:
        db: Async database session
        data: Design generation request with prompt and product type

    Returns:
        The newly created Design record
    """
    # Simulate AI image generation — in production, call OpenAI/Stable Diffusion
    style_prefix = f"[{data.style.upper()}] " if data.style else ""
    enhanced_prompt = f"{style_prefix}{data.prompt}"

    # Simulate generated image URL
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    image_url = (
        f"https://api.sweatshop.ai/designs/{data.product_type}/gen_{timestamp}.png"
    )

    design = Design(
        prompt=enhanced_prompt,
        image_url=image_url,
        product_type=data.product_type,
        status="draft",
    )
    db.add(design)
    await db.flush()
    return design


async def list_designs(
    db: AsyncSession,
    filters: Optional[DesignFilterParams] = None,
) -> list[Design]:
    """
    Retrieve designs with optional filtering.

    Args:
        db: Async database session
        filters: Optional filter parameters (status, product_type)

    Returns:
        List of Design records
    """
    query = select(Design).order_by(Design.created_at.desc())

    if filters:
        if filters.status:
            query = query.where(Design.status == filters.status)
        if filters.product_type:
            query = query.where(Design.product_type == filters.product_type)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_design(db: AsyncSession, design_id: int) -> Optional[Design]:
    """
    Retrieve a single design by ID.

    Args:
        db: Async database session
        design_id: The design's primary key

    Returns:
        The Design record, or None if not found
    """
    result = await db.execute(select(Design).where(Design.id == design_id))
    return result.scalar_one_or_none()


async def update_design(
    db: AsyncSession, design_id: int, data: DesignUpdate
) -> Optional[Design]:
    """
    Update an existing design.

    Args:
        db: Async database session
        design_id: The design's primary key
        data: Update data

    Returns:
        The updated Design, or None if not found
    """
    result = await db.execute(select(Design).where(Design.id == design_id))
    design = result.scalar_one_or_none()

    if not design:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(design, field, value)

    await db.flush()
    return design


async def approve_design(db: AsyncSession, design_id: int) -> Optional[DesignApprovalResponse]:
    """
    Approve a design, changing status from draft to approved.

    Args:
        db: Async database session
        design_id: The design's primary key

    Returns:
        Approval response, or None if not found
    """
    result = await db.execute(select(Design).where(Design.id == design_id))
    design = result.scalar_one_or_none()

    if not design:
        return None

    if design.status != "draft":
        return DesignApprovalResponse(
            success=False,
            design_id=design_id,
            status=design.status,
            message=f"Cannot approve design with status: {design.status}",
        )

    design.status = "approved"
    await db.flush()

    return DesignApprovalResponse(
        success=True,
        design_id=design_id,
        status="approved",
        message="Design approved successfully",
    )


async def reject_design(db: AsyncSession, design_id: int) -> Optional[DesignApprovalResponse]:
    """
    Reject a design — marks it as failed (not deleted).

    Args:
        db: Async database session
        design_id: The design's primary key

    Returns:
        Rejection response, or None if not found
    """
    result = await db.execute(select(Design).where(Design.id == design_id))
    design = result.scalar_one_or_none()

    if not design:
        return None

    if design.status not in ("draft", "approved"):
        return DesignApprovalResponse(
            success=False,
            design_id=design_id,
            status=design.status,
            message=f"Cannot reject design with status: {design.status}",
        )

    design.status = "rejected"
    await db.flush()

    return DesignApprovalResponse(
        success=True,
        design_id=design_id,
        status="rejected",
        message="Design rejected",
    )


async def create_design(db: AsyncSession, data: DesignCreate) -> Design:
    """
    Create a design record directly (not via AI generation).

    Args:
        db: Async database session
        data: Design creation data

    Returns:
        The newly created Design
    """
    design = Design(
        task_id=data.task_id,
        prompt=data.prompt,
        image_url=data.image_url,
        product_type=data.product_type,
        status="draft",
    )
    db.add(design)
    await db.flush()
    return design
