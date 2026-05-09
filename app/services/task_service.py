"""
Space Dungeon Sweatshop - Task Service
Business logic for task queue management.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task
from app.schemas import (
    TaskCancelResponse,
    TaskCreate,
    TaskFilterParams,
    TaskResponse,
    TaskRetryResponse,
    TaskUpdate,
)


async def create_task(db: AsyncSession, data: TaskCreate) -> Task:
    """
    Create a new task and add it to the queue.

    Args:
        db: Async database session
        data: Task creation data

    Returns:
        The newly created Task
    """
    task = Task(
        agent_id=data.agent_id,
        type=data.type,
        status=data.status,
        payload=data.payload,
        priority=data.priority,
    )
    db.add(task)
    await db.flush()
    return task


async def list_tasks(
    db: AsyncSession,
    filters: Optional[TaskFilterParams] = None,
) -> list[Task]:
    """
    Retrieve tasks with optional filtering.

    Args:
        db: Async database session
        filters: Optional filter parameters (status, agent, type)

    Returns:
        List of Task records matching filters
    """
    query = select(Task).order_by(Task.priority, Task.created_at)

    if filters:
        if filters.status:
            query = query.where(Task.status == filters.status)
        if filters.agent:
            query = query.where(Task.agent_id == filters.agent)
        if filters.type:
            query = query.where(Task.type == filters.type)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: int) -> Optional[Task]:
    """
    Retrieve a single task by ID.

    Args:
        db: Async database session
        task_id: The task's primary key

    Returns:
        The Task record, or None if not found
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def update_task(
    db: AsyncSession, task_id: int, data: TaskUpdate
) -> Optional[Task]:
    """
    Update an existing task.

    Args:
        db: Async database session
        task_id: The task's primary key
        data: Update data

    Returns:
        The updated Task, or None if not found
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.flush()
    return task


async def cancel_task(db: AsyncSession, task_id: int) -> Optional[TaskCancelResponse]:
    """
    Cancel a pending or running task.

    Args:
        db: Async database session
        task_id: The task's primary key

    Returns:
        Cancel response, or None if task not found
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        return None

    if task.status in ("completed", "failed"):
        return TaskCancelResponse(
            success=False,
            task_id=task_id,
            message=f"Cannot cancel task with status: {task.status}",
        )

    task.status = "failed"
    task.error = "Cancelled by user"
    task.completed_at = datetime.now(timezone.utc)
    await db.flush()

    return TaskCancelResponse(
        success=True,
        task_id=task_id,
        message="Task cancelled successfully",
    )


async def retry_task(db: AsyncSession, task_id: int) -> Optional[TaskRetryResponse]:
    """
    Retry a failed task by creating a new copy.

    Args:
        db: Async database session
        task_id: The failed task's primary key

    Returns:
        Retry response with new task ID, or None if not found
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        return None

    if task.status != "failed":
        return TaskRetryResponse(
            success=False,
            task_id=task_id,
            message=f"Can only retry failed tasks. Current status: {task.status}",
        )

    # Create a new task with the same parameters
    new_task = Task(
        agent_id=task.agent_id,
        type=task.type,
        status="pending",
        payload=task.payload,
        priority=max(1, task.priority - 1),  # Increase priority on retry
    )
    db.add(new_task)
    await db.flush()

    return TaskRetryResponse(
        success=True,
        task_id=task_id,
        new_task_id=new_task.id,
        message=f"Task retried as new task #{new_task.id}",
    )


async def get_agent_task_queue(db: AsyncSession, agent_name: str) -> list[Task]:
    """
    Get the pending task queue for a specific agent.

    Args:
        db: Async database session
        agent_name: The agent's name

    Returns:
        List of pending Task records for this agent
    """
    result = await db.execute(
        select(Task)
        .where(Task.agent_id == agent_name)
        .order_by(Task.priority, Task.created_at)
    )
    return list(result.scalars().all())
