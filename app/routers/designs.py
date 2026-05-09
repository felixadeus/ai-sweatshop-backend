"""
Space Dungeon Sweatshop - Designs Router
Design generation, gallery, and approval workflow.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    DesignApprovalResponse,
    DesignCreate,
    DesignFilterParams,
    DesignGenerateRequest,
    DesignResponse,
    DesignUpdate,
)
from app.services import design_service
from app.websocket import manager

router = APIRouter(prefix="/designs", tags=["designs"])


@router.get(
    "/",
    response_model=list[DesignResponse],
    summary="List all designs",
    description="Retrieve all designs with optional filters for status and product type.",
)
async def list_designs(
    status: str | None = Query(None, description="Filter by status (draft/approved/uploaded)"),
    product_type: str | None = Query(None, description="Filter by type (tshirt/mug/poster/candle/supplement)"),
    db: AsyncSession = Depends(get_db),
) -> list[DesignResponse]:
    """List designs with optional filtering."""
    filters = DesignFilterParams(status=status, product_type=product_type)
    designs = await design_service.list_designs(db, filters)
    return [DesignResponse.model_validate(d) for d in designs]


@router.post(
    "/generate",
    response_model=DesignResponse,
    status_code=201,
    summary="Generate design",
    description="Generate a new AI design from a prompt. Returns a design in 'draft' status.",
)
async def generate_design(
    data: DesignGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> DesignResponse:
    """Generate a new design using AI."""
    design = await design_service.generate_design(db, data)

    # Broadcast to WebSocket
    await manager.broadcast(
        "tasks",
        "design.generated",
        "Forge",
        {
            "design_id": design.id,
            "prompt": design.prompt,
            "product_type": design.product_type,
        },
    )

    return DesignResponse.model_validate(design)


@router.post(
    "/",
    response_model=DesignResponse,
    status_code=201,
    summary="Create design",
    description="Create a design record directly without AI generation.",
)
async def create_design(
    data: DesignCreate,
    db: AsyncSession = Depends(get_db),
) -> DesignResponse:
    """Create a design directly."""
    design = await design_service.create_design(db, data)
    return DesignResponse.model_validate(design)


@router.get(
    "/{design_id}",
    response_model=DesignResponse,
    summary="Get design details",
    description="Get detailed information for a specific design.",
)
async def get_design(
    design_id: int,
    db: AsyncSession = Depends(get_db),
) -> DesignResponse:
    """Get a single design by ID."""
    design = await design_service.get_design(db, design_id)
    if not design:
        raise HTTPException(status_code=404, detail=f"Design {design_id} not found")
    return DesignResponse.model_validate(design)


@router.patch(
    "/{design_id}",
    response_model=DesignResponse,
    summary="Update design",
    description="Update a design's properties.",
)
async def update_design(
    design_id: int,
    data: DesignUpdate,
    db: AsyncSession = Depends(get_db),
) -> DesignResponse:
    """Update a design."""
    design = await design_service.update_design(db, design_id, data)
    if not design:
        raise HTTPException(status_code=404, detail=f"Design {design_id} not found")
    return DesignResponse.model_validate(design)


@router.post(
    "/{design_id}/approve",
    response_model=DesignApprovalResponse,
    summary="Approve design",
    description="Approve a draft design, allowing it to proceed to product creation.",
)
async def approve_design(
    design_id: int,
    db: AsyncSession = Depends(get_db),
) -> DesignApprovalResponse:
    """Approve a design by ID."""
    result = await design_service.approve_design(db, design_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Design {design_id} not found")

    if result.success:
        await manager.broadcast(
            "tasks",
            "design.approved",
            "Forge",
            {"design_id": design_id, "status": "approved"},
        )

    return result


@router.post(
    "/{design_id}/reject",
    response_model=DesignApprovalResponse,
    summary="Reject design",
    description="Reject a design, preventing it from being used for products.",
)
async def reject_design(
    design_id: int,
    db: AsyncSession = Depends(get_db),
) -> DesignApprovalResponse:
    """Reject a design by ID."""
    result = await design_service.reject_design(db, design_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Design {design_id} not found")
    return result
