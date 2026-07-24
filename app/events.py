"""
Simple Server-Sent Events (SSE) manager for real-time updates.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class EventManager:
    """Manages SSE subscribers and broadcasts events."""

    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        """Add a new subscriber queue and return it."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        logger.debug(f"SSE subscriber added. Total: {len(self._subscribers)}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Remove a subscriber queue."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
            logger.debug(f"SSE subscriber removed. Total: {len(self._subscribers)}")

    async def broadcast(self, event: str, data: Dict[str, Any]):
        """Send an event to all connected subscribers."""
        message = {"event": event, "data": data}
        payload = json.dumps(message)
        dead_queues = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                dead_queues.append(queue)
        # Clean up full queues (disconnected clients)
        for q in dead_queues:
            self.unsubscribe(q)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# Global singleton
event_manager = EventManager()
