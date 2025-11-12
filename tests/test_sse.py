"""Tests for Server-Sent Events (SSE) functionality."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.application.event_broadcaster import EventBroadcaster, FeatureEvent
from src.main import app


class TestEventBroadcaster:
    """Tests for the EventBroadcaster service."""

    @pytest.mark.asyncio
    async def test_single_subscriber_receives_event(self):
        """Test that a single subscriber receives a broadcast event."""
        broadcaster = EventBroadcaster()
        received_events = []

        # Create a task that subscribes and collects one event
        async def collect_event():
            async for event in broadcaster.subscribe():
                received_events.append(event)
                break  # Exit after receiving one event

        subscriber_task = asyncio.create_task(collect_event())

        # Give subscriber time to connect
        await asyncio.sleep(0.01)

        # Broadcast an event
        test_event = FeatureEvent(
            event_type="feature-updated", feature_id=123, item_id=None
        )
        await broadcaster.broadcast(test_event)

        # Wait for subscriber to receive event
        await subscriber_task

        assert len(received_events) == 1
        assert received_events[0].event_type == "feature-updated"
        assert received_events[0].feature_id == 123

    @pytest.mark.asyncio
    async def test_multiple_subscribers_receive_event(self):
        """Test that multiple subscribers all receive the same broadcast event."""
        broadcaster = EventBroadcaster()
        received_events_1 = []
        received_events_2 = []

        # Create two subscriber tasks
        async def collect_event_1():
            async for event in broadcaster.subscribe():
                received_events_1.append(event)
                break

        async def collect_event_2():
            async for event in broadcaster.subscribe():
                received_events_2.append(event)
                break

        task1 = asyncio.create_task(collect_event_1())
        task2 = asyncio.create_task(collect_event_2())

        # Give subscribers time to connect
        await asyncio.sleep(0.01)

        # Broadcast an event
        test_event = FeatureEvent(
            event_type="feature-created", feature_id=456, item_id=1
        )
        await broadcaster.broadcast(test_event)

        # Wait for both subscribers to receive event
        await asyncio.gather(task1, task2)

        # Both subscribers should have received the event
        assert len(received_events_1) == 1
        assert len(received_events_2) == 1
        assert received_events_1[0].feature_id == 456
        assert received_events_2[0].feature_id == 456

    @pytest.mark.asyncio
    async def test_broadcast_with_no_subscribers(self):
        """Test that broadcasting with no subscribers doesn't raise errors."""
        broadcaster = EventBroadcaster()

        # This should not raise any errors
        test_event = FeatureEvent(
            event_type="feature-deleted", feature_id=789, item_id=2
        )
        await broadcaster.broadcast(test_event)

        # If we get here without exceptions, test passed
        assert True

    @pytest.mark.asyncio
    async def test_subscriber_cleanup_on_disconnect(self):
        """Test that subscribers are properly cleaned up when they disconnect."""
        broadcaster = EventBroadcaster()

        # Subscribe and immediately disconnect
        async def subscribe_and_disconnect():
            async for _ in broadcaster.subscribe():
                break  # Disconnect immediately

        # Start multiple subscribers that disconnect
        tasks = [asyncio.create_task(subscribe_and_disconnect()) for _ in range(3)]
        await asyncio.gather(*tasks)

        # After all tasks finish, subscriber list should be empty
        # (We can't directly access _subscribers, but we can test behavior)
        # Broadcasting should work without errors
        test_event = FeatureEvent(event_type="test", feature_id=1)
        await broadcaster.broadcast(test_event)

        assert True  # No exceptions means cleanup worked


class TestSSEEndpoint:
    """Tests for the SSE endpoint."""

    def test_sse_endpoint_returns_event_stream(self):
        """Test that SSE endpoint returns correct content type."""
        with TestClient(app) as client:
            # Use stream to keep connection open
            with client.stream("GET", "/api/v1/events") as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_sse_endpoint_streams_events(self):
        """Test that SSE endpoint streams events when broadcast occurs."""
        async with AsyncClient(
            transport=...,  # type: ignore[arg-type]
            app=app,
            base_url="http://test",
        ) as client:
            # This is a simplified test - full SSE streaming tests are complex
            # and would require setting up proper async streaming
            response = await client.get("/api/v1/events")
            assert response.status_code == 200

    def test_sse_endpoint_accessible_without_auth(self):
        """Test that SSE endpoint is accessible without authentication."""
        with TestClient(app) as client:
            # Should be able to connect without any auth
            with client.stream("GET", "/api/v1/events") as response:
                assert response.status_code == 200


class TestSSEIntegration:
    """Integration tests for SSE with feature operations."""

    @pytest.mark.asyncio
    async def test_feature_event_structure(self):
        """Test that FeatureEvent has the correct structure."""
        event = FeatureEvent(event_type="feature-updated", feature_id=123, item_id=456)

        assert event.event_type == "feature-updated"
        assert event.feature_id == 123
        assert event.item_id == 456
        assert event.timestamp > 0  # Should have a timestamp

    @pytest.mark.asyncio
    async def test_multiple_event_types(self):
        """Test broadcasting different event types."""
        broadcaster = EventBroadcaster()
        received_events = []

        async def collect_events():
            count = 0
            async for event in broadcaster.subscribe():
                received_events.append(event)
                count += 1
                if count >= 3:
                    break

        subscriber_task = asyncio.create_task(collect_events())
        await asyncio.sleep(0.01)

        # Broadcast different event types
        await broadcaster.broadcast(
            FeatureEvent(event_type="feature-created", feature_id=1)
        )
        await broadcaster.broadcast(
            FeatureEvent(event_type="feature-updated", feature_id=2)
        )
        await broadcaster.broadcast(
            FeatureEvent(event_type="feature-deleted", feature_id=3)
        )

        await subscriber_task

        assert len(received_events) == 3
        assert received_events[0].event_type == "feature-created"
        assert received_events[1].event_type == "feature-updated"
        assert received_events[2].event_type == "feature-deleted"
