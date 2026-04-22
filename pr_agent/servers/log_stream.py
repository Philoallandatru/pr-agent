"""
Real-time log streaming via WebSocket.

Provides WebSocket endpoint for streaming application logs in real-time
with filtering, search, and level-based controls.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Set, Optional
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect
from pr_agent.log import get_logger

logger = get_logger()


class LogLevel:
    """Log level constants."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogStreamManager:
    """Manages WebSocket connections for log streaming."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.log_buffer = []
        self.max_buffer_size = 1000
        self._handler = None

    def add_log_handler(self):
        """Add custom handler to capture logs."""
        if self._handler:
            return

        class WebSocketHandler(logging.Handler):
            def __init__(self, manager):
                super().__init__()
                self.manager = manager

            def emit(self, record):
                try:
                    log_entry = {
                        'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                        'level': record.levelname,
                        'logger': record.name,
                        'message': self.format(record),
                        'module': record.module,
                        'function': record.funcName,
                        'line': record.lineno
                    }

                    # Add to buffer
                    self.manager.log_buffer.append(log_entry)
                    if len(self.manager.log_buffer) > self.manager.max_buffer_size:
                        self.manager.log_buffer.pop(0)

                    # Broadcast to all connections
                    asyncio.create_task(self.manager.broadcast(log_entry))
                except Exception:
                    pass

        self._handler = WebSocketHandler(self)
        self._handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self._handler)

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, log_entry: dict):
        """Broadcast log entry to all connected clients."""
        if not self.active_connections:
            return

        message = json.dumps(log_entry)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def send_history(self, websocket: WebSocket, limit: int = 100):
        """Send recent log history to newly connected client."""
        history = self.log_buffer[-limit:] if limit else self.log_buffer
        for entry in history:
            try:
                await websocket.send_text(json.dumps(entry))
            except Exception:
                break

    def get_log_file_content(self, log_file: str, lines: int = 1000) -> list:
        """Read log file content."""
        try:
            log_path = Path(log_file)
            if not log_path.exists():
                return []

            with open(log_path, 'r') as f:
                all_lines = f.readlines()
                return [line.strip() for line in all_lines[-lines:]]
        except Exception as e:
            logger.error(f"Failed to read log file: {e}")
            return []


# Global instance
log_stream_manager = LogStreamManager()


async def handle_log_stream(websocket: WebSocket, level: Optional[str] = None, search: Optional[str] = None):
    """
    Handle WebSocket connection for log streaming.

    Args:
        websocket: WebSocket connection
        level: Minimum log level to stream (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        search: Search term to filter logs
    """
    await log_stream_manager.connect(websocket)

    try:
        # Send recent history
        await log_stream_manager.send_history(websocket, limit=100)

        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (for filtering updates, etc.)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Parse client message
                try:
                    message = json.loads(data)
                    command = message.get('command')

                    if command == 'ping':
                        await websocket.send_text(json.dumps({'type': 'pong'}))
                    elif command == 'get_history':
                        limit = message.get('limit', 100)
                        await log_stream_manager.send_history(websocket, limit)
                    elif command == 'clear':
                        # Send clear signal to client
                        await websocket.send_text(json.dumps({'type': 'clear'}))

                except json.JSONDecodeError:
                    pass

            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_text(json.dumps({'type': 'keepalive'}))
                except Exception:
                    break

    except WebSocketDisconnect:
        log_stream_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        log_stream_manager.disconnect(websocket)


def init_log_streaming():
    """Initialize log streaming system."""
    log_stream_manager.add_log_handler()
    logger.info("Log streaming initialized")


def get_log_stream_manager() -> LogStreamManager:
    """Get global log stream manager instance."""
    return log_stream_manager
