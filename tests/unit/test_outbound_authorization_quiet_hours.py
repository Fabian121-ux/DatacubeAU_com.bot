from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.outbound_authorization_service import OutboundAuthorizationService


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def test_quiet_hours_blocks_inside_same_day_window():
    config = {"start": "09:00", "end": "17:00", "timezone": "Africa/Lagos"}
    assert OutboundAuthorizationService._quiet_hours_active(config, _utc("2026-08-31T12:00:00+01:00")) is True
    assert OutboundAuthorizationService._quiet_hours_active(config, _utc("2026-08-31T18:00:00+01:00")) is False


def test_quiet_hours_blocks_cross_midnight_window():
    config = {"start": "22:00", "end": "07:00", "timezone": "Africa/Lagos"}
    assert OutboundAuthorizationService._quiet_hours_active(config, _utc("2026-08-31T23:30:00+01:00")) is True
    assert OutboundAuthorizationService._quiet_hours_active(config, _utc("2026-08-31T06:30:00+01:00")) is True
    assert OutboundAuthorizationService._quiet_hours_active(config, _utc("2026-08-31T08:00:00+01:00")) is False


def test_equal_quiet_hours_bounds_fail_safe_as_all_day_quiet():
    config = {"start": "00:00", "end": "00:00", "timezone": "Africa/Lagos"}
    assert OutboundAuthorizationService._quiet_hours_active(config, _utc("2026-08-31T12:00:00+01:00")) is True


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"start": "25:00", "end": "07:00", "timezone": "Africa/Lagos"},
        {"start": "22:00", "end": "07:00", "timezone": "No/Such_Zone"},
        {"start": "22:00", "end": "07:00"},
        "22:00-07:00@Africa/Lagos",
    ],
)
def test_invalid_quiet_hours_configuration_fails_closed(config):
    assert OutboundAuthorizationService._quiet_hours_active(config, _utc("2026-08-31T12:00:00+01:00")) is None


def test_missing_quiet_hours_is_not_a_block():
    assert OutboundAuthorizationService._quiet_hours_active(None, _utc("2026-08-31T12:00:00+01:00")) is False


def test_naive_instant_fails_closed_when_quiet_hours_are_configured():
    config = {"start": "22:00", "end": "07:00", "timezone": "Africa/Lagos"}
    assert OutboundAuthorizationService._quiet_hours_active(config, datetime(2026, 8, 31, 12, 0, 0)) is None
