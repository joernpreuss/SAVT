"""Event broadcaster for real-time SSE updates."""

import time
from asyncio import Queue
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Final

from ..logging_config import get_logger

logger: Final = get_logger(__name__)


@dataclass
class FeatureEvent:
    """Event representing a feature state change.

    Attributes:
        event_type: Type of event
            ("feature-updated", "feature-created", "feature-deleted")
        feature_id: ID of the affected feature
        item_id: Optional ID of the parent item (None for global features)
        timestamp: Unix timestamp when event was created
    """

    event_type: str
    feature_id: int
    item_id: int | None = None
    timestamp: float = field(default_factory=time.time)


class EventBroadcaster:
    """In-memory event broadcaster for SSE.

    Broadcasts feature change events to all connected SSE clients.
    Uses asyncio queues for concurrent subscriber management.

    Note: This implementation is for single-server deployments.
    For horizontal scaling, replace with Redis pub/sub or similar.
    """

    def __init__(self) -> None:
        self._subscribers: list[Queue[FeatureEvent]] = []
        logger.info("EventBroadcaster initialized")

    async def subscribe(self) -> AsyncIterator[FeatureEvent]:
        """Subscribe to events. Yields FeatureEvent objects.

        Automatically unsubscribes when iteration stops (e.g., client disconnects).
        """
        queue: Queue[FeatureEvent] = Queue()
        self._subscribers.append(queue)
        subscriber_count = len(self._subscribers)
        logger.info("New SSE subscriber", subscriber_count=subscriber_count)

        try:
            while True:
                event = await queue.get()
                logger.debug(
                    "Event delivered to subscriber",
                    event_type=event.event_type,
                    feature_id=event.feature_id,
                    item_id=event.item_id,
                )
                yield event
        finally:
            self._subscribers.remove(queue)
            remaining_count = len(self._subscribers)
            logger.info("SSE subscriber disconnected", remaining_count=remaining_count)

    async def broadcast(self, event: FeatureEvent) -> None:
        """Broadcast event to all subscribers.

        Args:
            event: FeatureEvent to broadcast to all connected clients
        """
        subscriber_count = len(self._subscribers)
        if subscriber_count == 0:
            logger.debug(
                "No subscribers for event",
                event_type=event.event_type,
                feature_id=event.feature_id,
            )
            return

        logger.info(
            "Broadcasting event",
            event_type=event.event_type,
            feature_id=event.feature_id,
            item_id=event.item_id,
            subscriber_count=subscriber_count,
        )

        for queue in self._subscribers:
            await queue.put(event)


# Global singleton instance
broadcaster = EventBroadcaster()
