from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scheduled_action_service import ScheduledActionService
from app.utils.time import utcnow


DEFAULT_OWNER_TIMEZONE = "Africa/Lagos"


@dataclass(frozen=True, slots=True)
class NaturalWhatsAppMessagePlan:
    target_reference: str
    message_text: str
    scheduled_for: datetime
    timezone: str
    date_phrase: str
    time_phrase: str


class NaturalActionPlannerService:
    """Conservative natural-language planner for owner-approved Zina actions.

    This service deliberately parses only a narrow WhatsApp scheduling grammar. It never
    sends directly to WAHA; execution is delegated to the existing ScheduledActionService.
    """

    _TIME = r"\d{1,2}(?::\d{2})?\s*(?:am|pm)?"
    _DATE = r"(?:today|tomorrow|[A-Za-z]{3,9}\s+\d{1,2}(?:,?\s+\d{4})?|\d{1,2}\s+[A-Za-z]{3,9}(?:,?\s+\d{4})?)"
    _SCHEDULE_PATTERNS = (
        re.compile(rf"^message\s+(?P<target>.+?)\s+at\s+(?P<time>{_TIME})\s+on\s+(?P<date>{_DATE})$", re.I),
        re.compile(rf"^message\s+(?P<target>.+?)\s+on\s+(?P<date>{_DATE})\s+at\s+(?P<time>{_TIME})$", re.I),
        re.compile(rf"^message\s+(?P<target>.+?)\s+(?P<date>today|tomorrow)\s+at\s+(?P<time>{_TIME})$", re.I),
        re.compile(rf"^message\s+(?P<target>.+?)\s+at\s+(?P<time>{_TIME})\s+(?P<date>today|tomorrow)$", re.I),
    )

    _MONTHS = {
        "jan": 1,
        "january": 1,
        "feb": 2,
        "february": 2,
        "mar": 3,
        "march": 3,
        "apr": 4,
        "april": 4,
        "may": 5,
        "jun": 6,
        "june": 6,
        "jul": 7,
        "july": 7,
        "aug": 8,
        "august": 8,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "oct": 10,
        "october": 10,
        "nov": 11,
        "november": 11,
        "dec": 12,
        "december": 12,
    }

    def __init__(self, session: AsyncSession):
        self.session = session
        self.scheduler = ScheduledActionService(session)

    @classmethod
    def parse(
        cls,
        instruction: str,
        *,
        timezone: str = DEFAULT_OWNER_TIMEZONE,
        now: datetime | None = None,
    ) -> NaturalWhatsAppMessagePlan | None:
        text = " ".join((instruction or "").strip().split())
        if not text or text.startswith("/"):
            return None
        text = re.sub(r"^@zina\s+", "", text, flags=re.I)
        text = re.sub(r"^please\s+", "", text, flags=re.I)
        if not text.lower().startswith("message "):
            return None

        command_text, message_text = cls._split_message_body(text)
        if not command_text or not message_text:
            return None

        match = next((pattern.match(command_text) for pattern in cls._SCHEDULE_PATTERNS if pattern.match(command_text)), None)
        if not match:
            return None

        target = " ".join(match.group("target").strip().split())
        date_phrase = " ".join(match.group("date").strip().split())
        time_phrase = " ".join(match.group("time").strip().split())
        if not target:
            return None

        try:
            tz = ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown timezone: {timezone}") from exc

        local_now = (now or utcnow()).astimezone(tz)
        scheduled_for = cls._parse_schedule(date_phrase, time_phrase, tz=tz, now=local_now)
        if scheduled_for <= local_now:
            raise ValueError("scheduled time must be in the future")

        return NaturalWhatsAppMessagePlan(
            target_reference=target,
            message_text=message_text,
            scheduled_for=scheduled_for,
            timezone=timezone,
            date_phrase=date_phrase,
            time_phrase=time_phrase,
        )

    async def create_from_instruction(
        self,
        instruction: str,
        *,
        timezone: str = DEFAULT_OWNER_TIMEZONE,
        source_message_id: int | None = None,
        requested_by_contact_id: int | None = None,
        idempotency_key: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        plan = self.parse(instruction, timezone=timezone, now=now)
        if plan is None:
            return None
        item = await self.scheduler.create_whatsapp_message(
            target_reference=plan.target_reference,
            text=plan.message_text,
            scheduled_for=plan.scheduled_for,
            timezone=plan.timezone,
            source_message_id=source_message_id,
            requested_by_contact_id=requested_by_contact_id,
            idempotency_key=idempotency_key,
        )
        return {
            "action": "whatsapp.send_message",
            "plan": {
                "target_reference": plan.target_reference,
                "scheduled_for": plan.scheduled_for,
                "timezone": plan.timezone,
                "date_phrase": plan.date_phrase,
                "time_phrase": plan.time_phrase,
            },
            "scheduled_action": item,
        }

    @staticmethod
    def _split_message_body(text: str) -> tuple[str | None, str | None]:
        tell_match = re.search(r"\s+and\s+tell\s+(?:him|her|them)\s+", text, flags=re.I)
        if tell_match:
            left = text[: tell_match.start()].strip()
            body = text[tell_match.end() :].strip()
            return (left or None, body or None)
        colon_index = text.find(":")
        if colon_index > 0:
            left = text[:colon_index].strip()
            body = text[colon_index + 1 :].strip()
            return (left or None, body or None)
        return None, None

    @classmethod
    def _parse_schedule(cls, date_phrase: str, time_phrase: str, *, tz: ZoneInfo, now: datetime) -> datetime:
        hour, minute = cls._parse_time(time_phrase)
        normalized_date = date_phrase.strip().lower().replace(",", "")
        if normalized_date == "today":
            date_value = now.date()
        elif normalized_date == "tomorrow":
            date_value = (now + timedelta(days=1)).date()
        else:
            tokens = normalized_date.split()
            if len(tokens) not in {2, 3}:
                raise ValueError("unsupported date format")
            if tokens[0] in cls._MONTHS:
                month = cls._MONTHS[tokens[0]]
                day = cls._parse_day(tokens[1])
                year = int(tokens[2]) if len(tokens) == 3 else now.year
            elif len(tokens) >= 2 and tokens[1] in cls._MONTHS:
                day = cls._parse_day(tokens[0])
                month = cls._MONTHS[tokens[1]]
                year = int(tokens[2]) if len(tokens) == 3 else now.year
            else:
                raise ValueError("unsupported date format")
            try:
                candidate = datetime(year, month, day, hour, minute, tzinfo=tz)
            except ValueError as exc:
                raise ValueError("invalid scheduled date") from exc
            if len(tokens) == 2 and candidate <= now:
                candidate = candidate.replace(year=year + 1)
            return candidate

        return datetime(date_value.year, date_value.month, date_value.day, hour, minute, tzinfo=tz)

    @staticmethod
    def _parse_day(value: str) -> int:
        day = int(value)
        if day < 1 or day > 31:
            raise ValueError("invalid scheduled day")
        return day

    @staticmethod
    def _parse_time(value: str) -> tuple[int, int]:
        match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", value.strip(), flags=re.I)
        if not match:
            raise ValueError("unsupported time format")
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = (match.group(3) or "").lower()
        if minute > 59:
            raise ValueError("invalid scheduled time")
        if meridiem:
            if hour < 1 or hour > 12:
                raise ValueError("invalid scheduled time")
            if hour == 12:
                hour = 0
            if meridiem == "pm":
                hour += 12
        elif hour > 23:
            raise ValueError("invalid scheduled time")
        return hour, minute
