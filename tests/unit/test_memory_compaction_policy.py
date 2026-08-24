from __future__ import annotations

import pytest

from app.models.enums import ChatType, Direction
from app.models.schema import Message
from app.services.memory_compaction_policy import (
    effective_summary_thresholds,
    expand_summary_thresholds,
    rolling_checkpoint,
)


def test_rolling_checkpoint_extends_default_summary_milestones() -> None:
    thresholds = (25, 50, 100)

    assert rolling_checkpoint(100, thresholds) is None
    assert rolling_checkpoint(149, thresholds) is None
    assert rolling_checkpoint(150, thresholds) == 150
    assert rolling_checkpoint(199, thresholds) == 150
    assert rolling_checkpoint(200, thresholds) == 200
    assert rolling_checkpoint(327, thresholds) == 300


def test_rolling_checkpoint_uses_last_configured_gap_and_single_threshold_fallback() -> None:
    assert rolling_checkpoint(75, (25, 50)) == 75
    assert rolling_checkpoint(99, (25, 50)) == 75
    assert rolling_checkpoint(100, (25, 50)) == 100
    assert rolling_checkpoint(59, (20,)) == 40
    assert rolling_checkpoint(60, (20,)) == 60


def test_expand_summary_thresholds_adds_only_latest_reached_checkpoint() -> None:
    assert expand_summary_thresholds(99, (25, 50, 100)) == (25, 50, 100)
    assert expand_summary_thresholds(150, (25, 50, 100)) == (25, 50, 100, 150)
    assert expand_summary_thresholds(327, (25, 50, 100)) == (25, 50, 100, 300)


@pytest.mark.asyncio
async def test_effective_summary_thresholds_uses_authoritative_message_count(db_session, test_contact) -> None:
    for index in range(151):
        db_session.add(
            Message(
                contact_id=test_contact.id,
                chat_id=test_contact.whatsapp_id,
                chat_type=ChatType.DM.value,
                direction=Direction.INBOUND.value if index % 2 == 0 else Direction.OUTBOUND.value,
                message_text=f"message {index}",
                normalized_text=f"message {index}",
            )
        )
    await db_session.flush()

    thresholds = await effective_summary_thresholds(
        db_session,
        test_contact.id,
        (25, 50, 100),
    )

    assert thresholds == (25, 50, 100, 150)
