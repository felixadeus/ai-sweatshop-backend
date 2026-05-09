"""
Space Dungeon Sweatshop - Agents Router
CRUD operations, status, commands, and efficiency for AI agents.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    AgentCommandRequest,
    AgentCommandResponse,
    AgentCreate,
    AgentResponse,
    AgentStatusResponse,
    AgentUpdate,
    EfficiencyReport,
    TaskResponse,
)
from app.services import agent_service
from app.websocket import manager

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get(
    "/",
    response_model=list[AgentResponse],
    summary="List all agents",
    description="Retrieve all AI agents with their current status and metrics.",
)
async def list_agents(
    db: AsyncSession = Depends(get_db),
) -> list[AgentResponse]:
    """Get all agents ordered by ID."""
    agents = await agent_service.list_agents(db)
    return [AgentResponse.model_validate(a) for a in agents]


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get single agent",
    description="Retrieve detailed information for a specific agent by ID.",
)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Get a single agent by ID."""
    agent = await agent_service.get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return AgentResponse.model_validate(agent)


@router.get(
    "/{agent_id}/status",
    response_model=AgentStatusResponse,
    summary="Get agent status",
    description="Get the current status and task of a specific agent.",
)
async def get_agent_status(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
) -> AgentStatusResponse:
    """Get an agent's current status and active task."""
    status = await agent_service.get_agent_status(db, agent_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return status


@router.post(
    "/",
    response_model=AgentResponse,
    status_code=201,
    summary="Create agent",
    description="Register a new AI agent in the system.",
)
async def create_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Create a new agent."""
    agent = await agent_service.create_agent(db, data)

    # Broadcast to WebSocket
    await manager.broadcast(
        "agents",
        "agent.created",
        str(agent.id),
        {"name": agent.name, "role": agent.role, "status": agent.status},
    )

    return AgentResponse.model_validate(agent)


@router.patch(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update agent",
    description="Update an agent's properties.",
)
async def update_agent(
    agent_id: int,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Update an agent's properties."""
    agent = await agent_service.update_agent(db, agent_id, data)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Broadcast status change if status was updated
    if data.status:
        await manager.broadcast(
            "agents",
            "agent.status_change",
            str(agent.id),
            {"status": agent.status, "name": agent.name},
        )

    return AgentResponse.model_validate(agent)


@router.post(
    "/{agent_id}/command",
    response_model=AgentCommandResponse,
    summary="Send command to agent",
    description="Send a control command to an agent (start, stop, pause, resume, restart, status).",
)
async def send_command(
    agent_id: int,
    request: AgentCommandRequest,
    db: AsyncSession = Depends(get_db),
) -> AgentCommandResponse:
    """Send a command to an agent."""
    result = await agent_service.execute_command(
        db, agent_id, request.command, request.params
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Broadcast command execution
    await manager.broadcast(
        "agents",
        "agent.command_executed",
        str(agent_id),
        {"command": request.command, "success": result.success},
    )

    return result


@router.get(
    "/{agent_id}/tasks",
    response_model=list[TaskResponse],
    summary="Get agent tasks",
    description="Get the task queue for a specific agent.",
)
async def get_agent_tasks(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    """Get all tasks assigned to a specific agent."""
    tasks = await agent_service.get_agent_tasks(db, agent_id)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.get(
    "/{agent_id}/efficiency",
    response_model=EfficiencyReport,
    summary="Get efficiency report",
    description="Generate an efficiency report for a specific agent.",
)
async def get_efficiency_report(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
) -> EfficiencyReport:
    """Get an agent's efficiency report."""
    report = await agent_service.get_efficiency_report(db, agent_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return report


@router.delete(
    "/{agent_id}",
    status_code=204,
    summary="Delete agent",
    description="Remove an agent from the system.",
)
async def delete_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an agent by ID."""
    deleted = await agent_service.delete_agent(db, agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
