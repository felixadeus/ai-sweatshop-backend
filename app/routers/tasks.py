"""
Space Dungeon Sweatshop - Tasks Router
Task queue management with CRUD and lifecycle operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    TaskCancelResponse,
    TaskCreate,
    TaskFilterParams,
    TaskResponse,
    TaskRetryResponse,
    TaskUpdate,
)
from app.services import task_service
from app.websocket import manager

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get(
    "/",
    response_model=list[TaskResponse],
    summary="List all tasks",
    description="Retrieve all tasks with optional filters for status, agent, and type.",
)
async def list_tasks(
    status: str | None = Query(None, description="Filter by status (pending/running/completed/failed)"),
    agent: str | None = Query(None, description="Filter by agent name"),
    type: str | None = Query(None, description="Filter by type (design/research/order/other)"),
    db: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    """List tasks with optional filtering."""
    filters = TaskFilterParams(status=status, agent=agent, type=type)
    tasks = await task_service.list_tasks(db, filters)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=201,
    summary="Create task",
    description="Create a new task and add it to the queue.",
)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Create a new task."""
    task = await task_service.create_task(db, data)

    # Broadcast to WebSocket
    await manager.broadcast(
        "tasks",
        "task.created",
        data.agent_id,
        {
            "task_id": task.id,
            "type": task.type,
            "priority": task.priority,
            "status": task.status,
        },
    )

    return TaskResponse.model_validate(task)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task details",
    description="Get detailed information for a specific task.",
)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Get a single task by ID."""
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update task",
    description="Update a task's properties such as status and result.",
)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Update a task's properties."""
    task = await task_service.update_task(db, task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Broadcast status change
    if data.status:
        await manager.broadcast(
            "tasks",
            f"task.{data.status}",
            task.agent_id,
            {"task_id": task.id, "status": task.status, "result": task.result},
        )

    return TaskResponse.model_validate(task)


@router.post(
    "/{task_id}/cancel",
    response_model=TaskCancelResponse,
    summary="Cancel task",
    description="Cancel a pending or running task.",
)
async def cancel_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> TaskCancelResponse:
    """Cancel a task by ID."""
    result = await task_service.cancel_task(db, task_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if result.success:
        await manager.broadcast(
            "tasks",
            "task.cancelled",
            "system",
            {"task_id": task_id},
        )

    return result


@router.post(
    "/{task_id}/retry",
    response_model=TaskRetryResponse,
    summary="Retry task",
    description="Retry a failed task by creating a new copy with higher priority.",
)
async def retry_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> TaskRetryResponse:
    """Retry a failed task."""
    result = await task_service.retry_task(db, task_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if result.success:
        await manager.broadcast(
            "tasks",
            "task.retried",
            "system",
            {"old_task_id": task_id, "new_task_id": result.new_task_id},
        )

    return result
