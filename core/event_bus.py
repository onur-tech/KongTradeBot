"""Simple async pub/sub event bus. No external infrastructure required."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List


Subscriber = Callable[["Event"], Awaitable[None]]


@dataclass
class Event:
    topic: str
    payload: Any
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    """Async pub/sub bus backed by asyncio.

    Usage::

        bus = EventBus()
        bus.subscribe("trade.signal", my_handler)
        await bus.publish(Event(topic="trade.signal", payload={...}))
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Subscriber]] = defaultdict(list)
        self._publish_count: int = 0

    # ── subscription management ───────────────────────────────────────────────

    def subscribe(self, topic: str, handler: Subscriber) -> None:
        """Register *handler* to receive events on *topic*."""
        if handler not in self._subscribers[topic]:
            self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Subscriber) -> None:
        """Remove *handler* from *topic*. Silent no-op if not registered."""
        try:
            self._subscribers[topic].remove(handler)
        except ValueError:
            pass

    # ── publishing ────────────────────────────────────────────────────────────

    async def publish(self, event: Event) -> int:
        """Deliver *event* to all subscribers of its topic.

        Handlers are called sequentially in subscription order.
        Returns the number of handlers called.
        """
        handlers = list(self._subscribers.get(event.topic, []))
        for handler in handlers:
            await handler(event)
        self._publish_count += 1
        return len(handlers)

    # ── introspection ─────────────────────────────────────────────────────────

    def subscriber_count(self, topic: str) -> int:
        return len(self._subscribers.get(topic, []))

    @property
    def publish_count(self) -> int:
        return self._publish_count
