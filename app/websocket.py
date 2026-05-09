"""
Space Dungeon Sweatshop - WebSocket Manager
Manages real-time connections and broadcasts across channels.
"""

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    Organized by channels: agents, tasks, sales, system.
    """

    def __init__(self) -> None:
        # Map channel names to lists of active WebSocket connections
        self._channels: dict[str, list[WebSocket]] = {
            "agents": [],
            "tasks": [],
            "sales": [],
            "system": [],
        }

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        """
        Accept a WebSocket connection and add it to a channel.

        Args:
            websocket: The WebSocket object to connect
            channel: The channel name (agents, tasks, sales, system)
        """
        await websocket.accept()
        if channel not in self._channels:
            self._channels[channel] = []
        self._channels[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str) -> None:
        """
        Remove a WebSocket connection from a channel.

        Args:
            websocket: The WebSocket object to disconnect
            channel: The channel name
        """
        if channel in self._channels:
            if websocket in self._channels[channel]:
                self._channels[channel].remove(websocket)

    async def broadcast(
        self,
        channel: str,
        message_type: str,
        agent_id: str,
        data: dict[str, Any],
    ) -> None:
        """
        Broadcast a message to all connected clients on a channel.

        Args:
            channel: The channel name to broadcast on
            message_type: Type of message (e.g., 'agent.status_change')
            agent_id: ID of the agent related to this message
            data: Payload data dictionary
        """
        if channel not in self._channels:
            return

        message = {
            "type": message_type,
            "agent_id": agent_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Send to all connected clients on the channel
        disconnected: list[WebSocket] = []
        for connection in self._channels[channel]:
            try:
                await connection.send_json(message)
            except RuntimeError:
                # Connection is closed, mark for removal
                disconnected.append(connection)

        # Clean up any dead connections
        for dead in disconnected:
            self.disconnect(dead, channel)

    async def send_personal(
        self,
        websocket: WebSocket,
        message_type: str,
        agent_id: str,
        data: dict[str, Any],
    ) -> None:
        """
        Send a message to a specific WebSocket connection.

        Args:
            websocket: The specific WebSocket to send to
            message_type: Type of message
            agent_id: ID of the agent
            data: Payload data dictionary
        """
        message = {
            "type": message_type,
            "agent_id": agent_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await websocket.send_json(message)

    def get_channel_stats(self) -> dict[str, int]:
        """
        Get the number of active connections per channel.

        Returns:
            Dictionary mapping channel names to connection counts
        """
        return {
            channel: len(connections)
            for channel, connections in self._channels.items()
        }


# Global singleton instance
manager = ConnectionManager()
