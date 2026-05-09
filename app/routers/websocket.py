"""
Space Dungeon Sweatshop - WebSocket Router
Real-time WebSocket endpoints for live dashboard updates.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket import manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/agents")
async def agents_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for agent status updates.
    Broadcasts: status changes, efficiency updates, command responses.
    """
    await manager.connect(websocket, "agents")
    try:
        # Send initial connection confirmation
        await manager.send_personal(
            websocket,
            "connection.established",
            "system",
            {"channel": "agents", "message": "Connected to agent updates"},
        )

        while True:
            # Keep the connection alive, waiting for client messages
            data = await websocket.receive_text()
            logger.debug(f"Received message on agents channel: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, "agents")
        logger.info("Agent WebSocket disconnected")
    except RuntimeError:
        manager.disconnect(websocket, "agents")


@router.websocket("/ws/tasks")
async def tasks_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for task queue updates.
    Broadcasts: new tasks, status changes, completions, cancellations.
    """
    await manager.connect(websocket, "tasks")
    try:
        await manager.send_personal(
            websocket,
            "connection.established",
            "system",
            {"channel": "tasks", "message": "Connected to task updates"},
        )

        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received message on tasks channel: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, "tasks")
        logger.info("Task WebSocket disconnected")
    except RuntimeError:
        manager.disconnect(websocket, "tasks")


@router.websocket("/ws/sales")
async def sales_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for live sales feed.
    Broadcasts: new orders, revenue updates, sync completions.
    """
    await manager.connect(websocket, "sales")
    try:
        await manager.send_personal(
            websocket,
            "connection.established",
            "system",
            {"channel": "sales", "message": "Connected to sales feed"},
        )

        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received message on sales channel: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, "sales")
        logger.info("Sales WebSocket disconnected")
    except RuntimeError:
        manager.disconnect(websocket, "sales")


@router.websocket("/ws/system")
async def system_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for system health and alerts.
    Broadcasts: system stats, health checks, error alerts.
    """
    await manager.connect(websocket, "system")
    try:
        await manager.send_personal(
            websocket,
            "connection.established",
            "system",
            {"channel": "system", "message": "Connected to system alerts"},
        )

        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received message on system channel: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, "system")
        logger.info("System WebSocket disconnected")
    except RuntimeError:
        manager.disconnect(websocket, "system")
