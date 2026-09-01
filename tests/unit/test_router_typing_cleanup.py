from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.router import InboundRouter


def _router_with_plan(plan: AsyncMock) -> InboundRouter:
    router = object.__new__(InboundRouter)
    router.reply_planner = SimpleNamespace(plan=plan)
    router._maybe_start_typing = AsyncMock(return_value=True)
    router._maybe_stop_typing = AsyncMock()
    return router


@pytest.mark.asyncio
async def test_owner_planning_stops_typing_after_success() -> None:
    planned = object()
    router = _router_with_plan(AsyncMock(return_value=planned))
    normalized = SimpleNamespace(chat_id="owner@c.us")

    result = await router._plan_with_owner_typing(
        normalized,
        7,
        owner_chat=True,
        wait_for_fabian_first=False,
    )

    assert result is planned
    router._maybe_start_typing.assert_awaited_once_with("owner@c.us")
    router._maybe_stop_typing.assert_awaited_once_with("owner@c.us")


@pytest.mark.asyncio
async def test_owner_planning_exception_preserves_error_and_stops_typing() -> None:
    planner_error = RuntimeError("planner failed")
    router = _router_with_plan(AsyncMock(side_effect=planner_error))
    router._maybe_stop_typing = AsyncMock(side_effect=RuntimeError("cleanup failed"))
    normalized = SimpleNamespace(chat_id="owner@c.us")

    with pytest.raises(RuntimeError, match="planner failed") as exc_info:
        await router._plan_with_owner_typing(
            normalized,
            8,
            owner_chat=True,
            wait_for_fabian_first=False,
        )

    assert exc_info.value is planner_error
    router._maybe_start_typing.assert_awaited_once_with("owner@c.us")
    router._maybe_stop_typing.assert_awaited_once_with("owner@c.us")


@pytest.mark.asyncio
async def test_owner_planning_cancellation_stops_typing_and_propagates() -> None:
    router = _router_with_plan(AsyncMock(side_effect=asyncio.CancelledError()))
    normalized = SimpleNamespace(chat_id="owner@c.us")

    with pytest.raises(asyncio.CancelledError):
        await router._plan_with_owner_typing(
            normalized,
            9,
            owner_chat=True,
            wait_for_fabian_first=False,
        )

    router._maybe_start_typing.assert_awaited_once_with("owner@c.us")
    router._maybe_stop_typing.assert_awaited_once_with("owner@c.us")


@pytest.mark.asyncio
async def test_external_contact_never_starts_planning_typing() -> None:
    planned = object()
    router = _router_with_plan(AsyncMock(return_value=planned))
    normalized = SimpleNamespace(chat_id="external@c.us")

    result = await router._plan_with_owner_typing(
        normalized,
        10,
        owner_chat=False,
        wait_for_fabian_first=False,
    )

    assert result is planned
    router._maybe_start_typing.assert_not_awaited()
    router._maybe_stop_typing.assert_not_awaited()
