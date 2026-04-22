"""
WebSocket handlers for real-time collaboration.
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
from pr_agent.collaboration import (
    get_collaboration_manager,
    User,
    UserStatus,
    EventType,
)

logger = logging.getLogger(__name__)


async def handle_collaboration_websocket(
    websocket: WebSocket,
    room_id: str,
    user_id: str,
    user_name: str,
    user_email: str,
):
    """
    Handle WebSocket connection for real-time collaboration.

    Args:
        websocket: FastAPI WebSocket connection
        room_id: Collaboration room ID
        user_id: User ID
        user_name: User display name
        user_email: User email
    """
    await websocket.accept()

    manager = get_collaboration_manager()
    room = manager.get_room(room_id)

    if not room:
        await websocket.send_json({
            "type": "error",
            "message": f"Room {room_id} not found"
        })
        await websocket.close()
        return

    # Create user object
    user = User(
        id=user_id,
        name=user_name,
        email=user_email,
        status=UserStatus.ACTIVE,
    )

    # Create message queue for this connection
    message_queue = asyncio.Queue()

    # Join room
    await manager.join_room(room_id, user, message_queue)

    try:
        # Start tasks for sending and receiving messages
        send_task = asyncio.create_task(
            _send_messages(websocket, message_queue)
        )
        receive_task = asyncio.create_task(
            _receive_messages(websocket, room, user_id)
        )

        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [send_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info(f"User {user_name} disconnected from room {room_id}")
    except Exception as e:
        logger.error(f"Error in collaboration WebSocket: {e}")
    finally:
        # Leave room
        await manager.leave_room(room_id, user_id)


async def _send_messages(websocket: WebSocket, queue: asyncio.Queue):
    """Send messages from queue to WebSocket."""
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise


async def _receive_messages(websocket: WebSocket, room, user_id: str):
    """Receive messages from WebSocket and process them."""
    try:
        while True:
            data = await websocket.receive_json()
            await _process_message(room, user_id, data)
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.error(f"Error receiving message: {e}")
        raise


async def _process_message(room, user_id: str, data: dict):
    """Process incoming WebSocket message."""
    message_type = data.get("type")

    if message_type == "cursor_move":
        await room.update_cursor(
            user_id,
            data["file_path"],
            data["line"],
            data["column"],
        )

    elif message_type == "add_comment":
        await room.add_comment(
            user_id,
            data["file_path"],
            data["line_number"],
            data["content"],
            data.get("parent_id"),
        )

    elif message_type == "update_comment":
        await room.update_comment(
            data["comment_id"],
            user_id,
            data["content"],
        )

    elif message_type == "delete_comment":
        await room.delete_comment(
            data["comment_id"],
            user_id,
        )

    elif message_type == "add_annotation":
        await room.add_annotation(
            user_id,
            data["file_path"],
            data["start_line"],
            data["end_line"],
            data["start_column"],
            data["end_column"],
            data["color"],
            data.get("label"),
        )

    elif message_type == "remove_annotation":
        await room.remove_annotation(
            data["annotation_id"],
            user_id,
        )

    elif message_type == "update_presence":
        status = UserStatus(data["status"])
        await room.update_presence(user_id, status)

    else:
        logger.warning(f"Unknown message type: {message_type}")
