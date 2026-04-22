"""Tests for core/event_bus.py."""
import asyncio
import pytest
import pytest_asyncio

from core.event_bus import Event, EventBus


pytestmark = pytest.mark.asyncio


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


# ── single subscriber ─────────────────────────────────────────────────────────

async def test_single_subscriber_receives_event(bus: EventBus):
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe("test.topic", handler)
    evt = Event(topic="test.topic", payload={"x": 1})
    count = await bus.publish(evt)

    assert count == 1
    assert len(received) == 1
    assert received[0].payload == {"x": 1}


# ── multiple subscribers ──────────────────────────────────────────────────────

async def test_multiple_subscribers_all_receive(bus: EventBus):
    calls: list[str] = []

    async def h1(e: Event) -> None:
        calls.append("h1")

    async def h2(e: Event) -> None:
        calls.append("h2")

    bus.subscribe("sig", h1)
    bus.subscribe("sig", h2)
    await bus.publish(Event(topic="sig", payload=None))

    assert sorted(calls) == ["h1", "h2"]


# ── unsubscribe ───────────────────────────────────────────────────────────────

async def test_unsubscribe_stops_delivery(bus: EventBus):
    calls: list[int] = []

    async def h(e: Event) -> None:
        calls.append(1)

    bus.subscribe("t", h)
    await bus.publish(Event(topic="t", payload=None))
    bus.unsubscribe("t", h)
    await bus.publish(Event(topic="t", payload=None))

    assert calls == [1]


async def test_unsubscribe_unknown_handler_is_silent(bus: EventBus):
    async def h(e: Event) -> None:
        pass

    bus.unsubscribe("nonexistent", h)  # must not raise


# ── unknown topic ─────────────────────────────────────────────────────────────

async def test_publish_to_unknown_topic_returns_zero(bus: EventBus):
    count = await bus.publish(Event(topic="no.subscribers", payload=42))
    assert count == 0


# ── publish_count ─────────────────────────────────────────────────────────────

async def test_publish_count_increments(bus: EventBus):
    async def noop(e: Event) -> None:
        pass

    bus.subscribe("a", noop)
    assert bus.publish_count == 0
    await bus.publish(Event(topic="a", payload=None))
    await bus.publish(Event(topic="a", payload=None))
    assert bus.publish_count == 2


# ── subscriber_count ──────────────────────────────────────────────────────────

async def test_subscriber_count(bus: EventBus):
    async def h(e: Event) -> None:
        pass

    assert bus.subscriber_count("x") == 0
    bus.subscribe("x", h)
    assert bus.subscriber_count("x") == 1
    bus.unsubscribe("x", h)
    assert bus.subscriber_count("x") == 0


# ── duplicate subscribe is idempotent ─────────────────────────────────────────

async def test_duplicate_subscribe_is_idempotent(bus: EventBus):
    calls: list[int] = []

    async def h(e: Event) -> None:
        calls.append(1)

    bus.subscribe("d", h)
    bus.subscribe("d", h)  # second call — should be ignored
    await bus.publish(Event(topic="d", payload=None))
    assert calls == [1]
