"""Long-thread conversation summary checkpoint policy.

Keeps the configured summary milestones intact while extending them with one
rolling checkpoint after the final milestone so long-running conversations do
not stop producing fresh compact context.
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import Message


def rolling_checkpoint(
    message_count: int,
    configured_thresholds: Sequence[int],
) -> int | None:
    """Return the latest rolling checkpoint beyond the final configured milestone.

    The rolling interval follows the gap between the last two configured
    thresholds. With the default 25/50/100 milestones this produces 150, 200,
    250, ... . A single configured threshold repeats at that threshold's size.

    Only the latest reached checkpoint is returned. If processing was paused
    for a long time, Zina creates one fresh summary rather than several
    identical catch-up summaries for historical checkpoints.
    """
    thresholds = sorted({int(value) for value in configured_thresholds if int(value) > 0})
    if not thresholds:
        return None

    final_threshold = thresholds[-1]
    if message_count <= final_threshold:
        return None

    if len(thresholds) >= 2:
        interval = final_threshold - thresholds[-2]
    else:
        interval = final_threshold
    interval = max(1, interval)

    completed_windows = (message_count - final_threshold) // interval
    if completed_windows < 1:
        return None
    return final_threshold + (completed_windows * interval)


def expand_summary_thresholds(
    message_count: int,
    configured_thresholds: Sequence[int],
) -> tuple[int, ...]:
    """Return configured milestones plus the latest due rolling checkpoint."""
    thresholds = sorted({int(value) for value in configured_thresholds if int(value) > 0})
    checkpoint = rolling_checkpoint(message_count, thresholds)
    if checkpoint is not None:
        thresholds.append(checkpoint)
    return tuple(sorted(set(thresholds)))


async def effective_summary_thresholds(
    session: AsyncSession,
    contact_id: int,
    configured_thresholds: Sequence[int],
) -> tuple[int, ...]:
    """Resolve long-thread summary thresholds from authoritative message history."""
    message_count = (
        await session.execute(select(func.count(Message.id)).where(Message.contact_id == contact_id))
    ).scalar_one()
    return expand_summary_thresholds(int(message_count or 0), configured_thresholds)
