"""
Space Dungeon Sweatshop - Agent Service
Business logic for AI agent management.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Task
from app.schemas import (
    AgentCommandResponse,
    AgentCreate,
    AgentStatusResponse,
    AgentUpdate,
    EfficiencyReport,
)


async def list_agents(db: AsyncSession) -> list[Agent]:
    """
    Retrieve all agents ordered by ID.

    Args:
        db: Async database session

    Returns:
        List of all Agent records
    """
    result = await db.execute(select(Agent).order_by(Agent.id))
    return list(result.scalars().all())


async def get_agent(db: AsyncSession, agent_id: int) -> Optional[Agent]:
    """
    Retrieve a single agent by ID.

    Args:
        db: Async database session
        agent_id: The agent's primary key

    Returns:
        The Agent record, or None if not found
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def get_agent_status(db: AsyncSession, agent_id: int) -> Optional[AgentStatusResponse]:
    """
    Get an agent's current status and task.

    Args:
        db: Async database session
        agent_id: The agent's primary key

    Returns:
        AgentStatusResponse with status details, or None
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        return None

    return AgentStatusResponse(
        id=agent.id,
        name=agent.name,
        status=agent.status,
        current_task=agent.current_task,
        efficiency_pct=agent.efficiency_pct,
        updated_at=datetime.now(timezone.utc),
    )


async def create_agent(db: AsyncSession, data: AgentCreate) -> Agent:
    """
    Create a new agent record.

    Args:
        db: Async database session
        data: Agent creation data

    Returns:
        The newly created Agent
    """
    agent = Agent(
        name=data.name,
        role=data.role,
        status=data.status,
        efficiency_pct=data.efficiency_pct,
        tasks_completed=data.tasks_completed,
        current_task=data.current_task,
    )
    db.add(agent)
    await db.flush()
    return agent


async def update_agent(db: AsyncSession, agent_id: int, data: AgentUpdate) -> Optional[Agent]:
    """
    Update an existing agent's properties.

    Args:
        db: Async database session
        agent_id: The agent's primary key
        data: Update data (only non-None fields are updated)

    Returns:
        The updated Agent, or None if not found
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.flush()
    return agent


async def delete_agent(db: AsyncSession, agent_id: int) -> bool:
    """
    Delete an agent by ID.

    Args:
        db: Async database session
        agent_id: The agent's primary key

    Returns:
        True if deleted, False if not found
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        return False

    await db.delete(agent)
    await db.flush()
    return True


async def execute_command(
    db: AsyncSession,
    agent_id: int,
    command: str,
    params: dict[str, Any],
) -> Optional[AgentCommandResponse]:
    """
    Execute a command on an agent.

    Args:
        db: Async database session
        agent_id: The agent's primary key
        command: The command string to execute
        params: Additional command parameters

    Returns:
        Command response, or None if agent not found
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        return None

    # Simulate command execution
    valid_commands = ["start", "stop", "pause", "resume", "restart", "status"]

    if command not in valid_commands:
        return AgentCommandResponse(
            success=False,
            message=f"Unknown command: '{command}'. Valid: {valid_commands}",
            agent_id=agent_id,
            command=command,
            executed_at=datetime.now(timezone.utc),
        )

    # Update agent state based on command
    if command == "start" or command == "resume":
        agent.status = "working"
    elif command == "stop" or command == "pause":
        agent.status = "idle"
        agent.current_task = None
    elif command == "restart":
        agent.status = "working"
        agent.efficiency_pct = 100.0

    await db.flush()

    return AgentCommandResponse(
        success=True,
        message=f"Command '{command}' executed on {agent.name}",
        agent_id=agent_id,
        command=command,
        executed_at=datetime.now(timezone.utc),
    )


async def get_agent_tasks(db: AsyncSession, agent_id: int) -> list[Task]:
    """
    Get all tasks assigned to a specific agent.

    Args:
        db: Async database session
        agent_id: The agent's ID (string name)

    Returns:
        List of Task records for this agent
    """
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        return []

    result = await db.execute(
        select(Task)
        .where(Task.agent_id == agent.name)
        .order_by(Task.created_at.desc())
    )
    return list(result.scalars().all())


async def get_efficiency_report(
    db: AsyncSession, agent_id: int
) -> Optional[EfficiencyReport]:
    """
    Generate an efficiency report for an agent.

    Args:
        db: Async database session
        agent_id: The agent's primary key

    Returns:
        EfficiencyReport, or None if agent not found
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        return None

    # Count failed tasks for this agent
    result = await db.execute(
        select(func.count(Task.id)).where(
            Task.agent_id == agent.name,
            Task.status == "failed",
        )
    )
    failed_count = result.scalar() or 0

    return EfficiencyReport(
        agent_id=agent.id,
        agent_name=agent.name,
        efficiency_pct=agent.efficiency_pct,
        tasks_completed=agent.tasks_completed,
        tasks_failed=failed_count,
        avg_task_duration_seconds=None,
        report_generated_at=datetime.now(timezone.utc),
    )
