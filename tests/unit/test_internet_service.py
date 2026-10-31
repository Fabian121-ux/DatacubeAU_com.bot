from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.internet_service import InternetService
from app.services.internet_service import InternetServiceError


def test_parse_user_command() -> None:
    service, command, query = InternetService.parse_user_command("!search latest AI news")

    assert service == "web"
    assert command == "!search"
    assert query == "latest AI news"


def test_parse_gif_command() -> None:
    service, command, query = InternetService.parse_user_command("!gif celebration")

    assert service == "gif"
    assert command == "!gif"
    assert query == "celebration"


def test_parse_user_command_ignores_normal_messages() -> None:
    service, command, query = InternetService.parse_user_command("hello")

    assert service is None
    assert command == ""
    assert query == ""


def test_detect_live_service() -> None:
    assert InternetService.detect_live_service("weather in Lagos today") == "weather"
    assert InternetService.detect_live_service("convert 100 USD to NGN") == "currency"
    assert InternetService.detect_live_service("latest AI policy news") == "web"
    assert InternetService.detect_live_service("tell me about Datacube AU") is None


def test_parse_currency() -> None:
    amount, source, target = InternetService.parse_currency("100 usd to ngn")

    assert amount == 100
    assert source == "USD"
    assert target == "NGN"


def test_disabled_message_guides_user_and_owner() -> None:
    message = InternetService.disabled_message("web", explicit_command="!search", reason="internet_disabled")

    assert "!search <query>" in message
    assert "/internet on" in message


def test_clean_location_query_removes_weather_words() -> None:
    assert InternetService.clean_location_query("weather in Lagos today") == "lagos"


@dataclass
class FakeCache:
    answer_text: str = "Cached internet answer."
    response_json: dict[str, str] | None = None


class CacheFirstInternetService(InternetService):
    async def lookup_cache(self, *_):
        return FakeCache(response_json={"__provider": "searxng"})

    async def record_usage(self, *_, **__):
        return None

    async def _enabled_status(self, *_):
        raise AssertionError("enabled status should not run before cache lookup")


@pytest.mark.asyncio
async def test_run_uses_internet_cache_before_enabled_checks() -> None:
    service = CacheFirstInternetService.__new__(CacheFirstInternetService)

    result = await InternetService.run(service, "web", "latest waha release", contact_id=1)

    assert result.cache_hit is True
    assert result.reply_text == "Cached internet answer."
    assert result.provider == "searxng"


class CurrencyFallbackInternetService(InternetService):
    async def _currency_frankfurter(self, *_):
        raise InternetServiceError("missing pair")

    async def _currency_exchangerate_host(self, *_):
        return 160000.0, 1600.0, {"provider": "exchangerate.host"}


@pytest.mark.asyncio
async def test_currency_uses_exchangerate_host_fallback() -> None:
    service = CurrencyFallbackInternetService.__new__(CurrencyFallbackInternetService)

    answer, payload, provider, media = await InternetService._currency(service, "100 USD to NGN")

    assert "100 USD = 160,000.00 NGN" in answer
    assert payload == {"provider": "exchangerate.host"}
    assert provider == "exchangerate.host"
    assert media is None
