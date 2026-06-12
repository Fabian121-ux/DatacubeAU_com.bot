from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import re
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.schema import Contact, InternetCache, InternetUsageEvent
from app.services.bot_config_service import BotConfigService
from app.utils.text import normalize_text
from app.utils.time import utcnow


INTERNET_COMMANDS = {
    "!search": "web",
    "!google": "web",
    "!news": "news",
    "!weather": "weather",
    "!currency": "currency",
    "!youtube": "youtube",
    "!image": "image",
    "!sticker": "sticker",
    "!gif": "gif",
}

SERVICE_CONFIG_KEYS = {
    "web": "web_search_enabled",
    "news": "news_enabled",
    "weather": "weather_enabled",
    "currency": "currency_enabled",
    "youtube": "youtube_enabled",
    "image": "image_search_enabled",
    "sticker": "sticker_search_enabled",
    "gif": "sticker_search_enabled",
}

SERVICE_SETTING_DEFAULTS = {
    "web": "web_search_enabled",
    "news": "news_enabled",
    "weather": "weather_enabled",
    "currency": "currency_enabled",
    "youtube": "youtube_enabled",
    "image": "image_search_enabled",
    "sticker": "sticker_search_enabled",
    "gif": "sticker_search_enabled",
}

SEARXNG_CATEGORIES = {
    "web": "general",
    "news": "news",
    "youtube": "videos",
    "image": "images",
    "sticker": "images",
}


@dataclass(slots=True)
class InternetResult:
    service: str
    query: str
    reply_text: str
    provider: str = "none"
    cache_hit: bool = False
    success: bool = True
    diagnostics: dict[str, Any] | None = None
    media_url: str | None = None
    media_type: str | None = None
    media_caption: str | None = None


class InternetService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.config = BotConfigService(session)

    @staticmethod
    def parse_user_command(text_value: str) -> tuple[str | None, str, str]:
        stripped = text_value.strip()
        if not stripped.startswith("!"):
            return None, "", ""
        command, _, query = stripped.partition(" ")
        command = command.lower().strip()
        service = INTERNET_COMMANDS.get(command)
        return service, command, query.strip()

    async def handle_user_command(self, message, contact: Contact | None) -> InternetResult | None:
        service, command, query = self.parse_user_command(message.message_text)
        if not service:
            return None
        if not query:
            return InternetResult(
                service=service,
                query=query,
                reply_text=self.usage_for_command(command),
                success=False,
                diagnostics={"internet": {"command": command, "valid": False}},
            )
        return await self.run(service, query, contact_id=getattr(contact, "id", None), explicit_command=command)

    async def maybe_live_lookup(self, query: str, contact_id: int | None) -> InternetResult | None:
        if not await self.config.get_bool("internet_smart_detection_enabled", settings.internet_smart_detection_enabled):
            return None
        service = self.detect_live_service(query)
        if not service:
            return None
        return await self.run(service, query, contact_id=contact_id, explicit_command=None, smart_detected=True)

    async def run(
        self,
        service: str,
        query: str,
        *,
        contact_id: int | None,
        explicit_command: str | None = None,
        smart_detected: bool = False,
    ) -> InternetResult:
        cached = await self.lookup_cache(service, query)
        if cached:
            payload = cached.response_json or {}
            await self.record_usage(contact_id, service=service, query=query, provider="cache", cache_hit=True, success=True)
            return InternetResult(
                service=service,
                query=query,
                reply_text=cached.answer_text,
                provider=str(payload.get("__provider") or "cache"),
                cache_hit=True,
                diagnostics={"internet": {"cache_hit": True, "service": service, "provider": payload.get("__provider") or "cache"}},
                media_url=payload.get("__media_url"),
                media_type=payload.get("__media_type"),
                media_caption=payload.get("__media_caption"),
            )

        enabled_check = await self._enabled_status(service)
        if not enabled_check["enabled"]:
            await self.record_usage(
                contact_id,
                service=service,
                query=query,
                provider="disabled",
                cache_hit=False,
                success=False,
                error_message=str(enabled_check["reason"]),
            )
            return InternetResult(
                service=service,
                query=query,
                reply_text=self.disabled_message(service, explicit_command=explicit_command, reason=enabled_check["reason"]),
                success=False,
                diagnostics={"internet": {"enabled": False, "reason": enabled_check["reason"], "service": service}},
            )

        quota = await self.check_quota(contact_id)
        if not quota["allowed"]:
            return InternetResult(
                service=service,
                query=query,
                reply_text=(
                    "*Internet Limit Reached*\n\n"
                    f"Used:\n{quota['used']}/{quota['limit']}\n\n"
                    "Please try again tomorrow."
                ),
                success=False,
                diagnostics={"internet": {"quota": quota, "service": service}},
            )

        provider = await self.config.get("internet_provider", settings.internet_provider)
        try:
            answer, payload, provider_used, media = await self.fetch(service, query, provider=provider)
            payload = dict(payload or {})
            payload["__provider"] = provider_used
            if media:
                payload.update(
                    {
                        "__media_url": media.get("url"),
                        "__media_type": media.get("type"),
                        "__media_caption": media.get("caption"),
                    }
                )
            await self.upsert_cache(service, query, answer, payload)
            await self.record_usage(contact_id, service=service, query=query, provider=provider_used, cache_hit=False, success=True)
            return InternetResult(
                service=service,
                query=query,
                reply_text=answer,
                provider=provider_used,
                diagnostics={
                    "internet": {
                        "cache_hit": False,
                        "service": service,
                        "provider": provider_used,
                        "smart_detected": smart_detected,
                    }
                },
                media_url=media.get("url") if media else None,
                media_type=media.get("type") if media else None,
                media_caption=media.get("caption") if media else None,
            )
        except InternetServiceError as exc:
            await self.record_usage(
                contact_id,
                service=service,
                query=query,
                provider=provider,
                cache_hit=False,
                success=False,
                error_message=str(exc),
            )
            return InternetResult(
                service=service,
                query=query,
                reply_text=f"*Internet Service Unavailable*\n\n{exc}",
                provider=provider,
                success=False,
                diagnostics={"internet": {"service": service, "provider": provider, "error": str(exc)}},
            )

    async def fetch(self, service: str, query: str, *, provider: str) -> tuple[str, dict[str, Any], str, dict[str, str] | None]:
        if service == "weather":
            return await self._weather(query)
        if service == "currency":
            return await self._currency(query)
        if service == "youtube":
            return await self._youtube(query, provider=provider)
        if service == "image":
            return await self._image(query, provider=provider)
        if service == "gif":
            return await self._giphy(query, media_kind="gifs")
        if service == "sticker":
            return await self._sticker(query, provider=provider)
        if service == "news":
            return await self._news(query, provider=provider)
        return await self._web(query, provider=provider)

    async def _web(self, query: str, *, provider: str) -> tuple[str, dict[str, Any], str, None]:
        if provider == "tavily" and settings.tavily_api_key:
            return await self._tavily(query, title="Web Search")
        if provider == "brave" and settings.brave_search_api_key:
            return await self._brave_search_endpoint(
                "web",
                query,
                title="Web Search",
                url="https://api.search.brave.com/res/v1/web/search",
            )
        return await self._searxng(query, title="Web Search", service="web")

    async def _news(self, query: str, *, provider: str) -> tuple[str, dict[str, Any], str, None]:
        if provider == "brave" and settings.brave_search_api_key:
            return await self._brave_search_endpoint(
                "news",
                query,
                title="News",
                url="https://api.search.brave.com/res/v1/news/search",
            )
        if provider == "tavily" and settings.tavily_api_key:
            return await self._tavily(f"latest news {query}", title="News")
        return await self._searxng(query, title="News", service="news")

    async def _youtube(self, query: str, *, provider: str) -> tuple[str, dict[str, Any], str, None]:
        if settings.youtube_api_key:
            url = "https://www.googleapis.com/youtube/v3/search"
            payload = await self._get(
                url,
                params={
                    "part": "snippet",
                    "type": "video",
                    "maxResults": "5",
                    "q": query,
                    "key": settings.youtube_api_key,
                },
                headers={},
            )
            items = []
            for item in payload.get("items", [])[:5]:
                video_id = (item.get("id") or {}).get("videoId")
                snippet = item.get("snippet") or {}
                if video_id:
                    items.append(
                        {
                            "title": snippet.get("title") or "YouTube video",
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "description": snippet.get("description") or "",
                        }
                    )
            return self._format_results("YouTube", query, items), payload, "youtube", None
        searx_query = query if "youtube" in normalize_text(query) else f"site:youtube.com {query}"
        return await self._searxng(searx_query, title="YouTube", service="youtube")

    async def _image(self, query: str, *, provider: str) -> tuple[str, dict[str, Any], str, None]:
        if provider == "brave" and settings.brave_search_api_key:
            return await self._brave_search_endpoint(
                "image",
                query,
                title="Image Search",
                url="https://api.search.brave.com/res/v1/images/search",
            )
        return await self._searxng(query, title="Image Search", service="image")

    async def _sticker(self, query: str, *, provider: str) -> tuple[str, dict[str, Any], str, dict[str, str] | None]:
        if settings.giphy_api_key:
            return await self._giphy(query, media_kind="stickers")
        return await self._searxng(f"{query} sticker transparent png", title="Sticker Search", service="sticker")

    async def _giphy(self, query: str, *, media_kind: str) -> tuple[str, dict[str, Any], str, dict[str, str] | None]:
        if not settings.giphy_api_key:
            raise InternetServiceError("Giphy media requires GIPHY_API_KEY.")
        endpoint = "stickers" if media_kind == "stickers" else "gifs"
        payload = await self._get(
            f"https://api.giphy.com/v1/{endpoint}/search",
            params={"api_key": settings.giphy_api_key, "q": query, "limit": "5", "rating": "g"},
            headers={},
        )
        items = []
        media_url = None
        title = "GIF"
        for item in payload.get("data", [])[:5]:
            images = item.get("images") or {}
            original = images.get("original") or {}
            fixed_height = images.get("fixed_height") or {}
            url = original.get("url") or fixed_height.get("url") or item.get("url") or ""
            title = item.get("title") or title
            if not media_url and url:
                media_url = url
            items.append({"title": title, "url": url or item.get("url") or "", "description": item.get("url") or ""})
        label = "Giphy"
        answer = self._format_results(label, query, items)
        media = {"url": media_url, "type": "image", "caption": f"{label}: {title}"} if media_url else None
        return answer, payload, "giphy", media

    async def _weather(self, query: str) -> tuple[str, dict[str, Any], str, None]:
        location = self.clean_location_query(query)
        geo_payload = await self._nominatim_geocode(location)
        if not geo_payload:
            raise InternetServiceError(f"Could not find location: {location}")
        place = geo_payload[0]
        latitude = str(place.get("lat") or "")
        longitude = str(place.get("lon") or "")
        if not latitude or not longitude:
            raise InternetServiceError(f"Could not find coordinates for: {location}")
        weather_payload = await self._get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
            headers={},
        )
        current = weather_payload.get("current") or {}
        code = current.get("weather_code")
        display_name = place.get("display_name") or location
        lines = [
            f"*Weather*\n\nLocation:\n{self._short_place_name(display_name)}",
            "",
            f"Condition:\n{self.weather_code_label(code)}",
            "",
            f"Temperature:\n{current.get('temperature_2m', 'Unknown')}°C",
            "",
            f"Feels Like:\n{current.get('apparent_temperature', 'Unknown')}°C",
            "",
            f"Humidity:\n{current.get('relative_humidity_2m', 'Unknown')}%",
            "",
            f"Wind:\n{current.get('wind_speed_10m', 'Unknown')} km/h",
        ]
        return "\n".join(lines), {"geocoding": geo_payload, "weather": weather_payload}, "open-meteo", None

    async def _currency(self, query: str) -> tuple[str, dict[str, Any], str, None]:
        amount, from_code, to_code = self.parse_currency(query)
        errors: list[str] = []
        for provider_name, converter in (
            ("frankfurter", self._currency_frankfurter),
            ("exchangerate.host", self._currency_exchangerate_host),
        ):
            try:
                result, rate, payload = await converter(amount, from_code, to_code)
            except InternetServiceError as exc:
                errors.append(f"{provider_name}: {exc}")
                continue
            if result is not None:
                return (
                    f"*Currency*\n\n{amount:g} {from_code} = {float(result):,.2f} {to_code}\n\nRate:\n{rate}",
                    payload,
                    provider_name,
                    None,
                )
        raise InternetServiceError("Could not convert currency. " + " | ".join(errors))

    async def _currency_frankfurter(self, amount: float, from_code: str, to_code: str) -> tuple[float | None, float | None, dict[str, Any]]:
        payload = await self._get(
            "https://api.frankfurter.app/latest",
            params={"amount": str(amount), "from": from_code, "to": to_code},
            headers={},
        )
        rates = payload.get("rates") or {}
        result = rates.get(to_code)
        rate = (float(result) / amount) if result is not None and amount else None
        if result is None:
            raise InternetServiceError(f"{to_code} unavailable")
        return float(result), rate, payload

    async def _currency_exchangerate_host(self, amount: float, from_code: str, to_code: str) -> tuple[float | None, float | None, dict[str, Any]]:
        payload = await self._get(
            "https://api.exchangerate.host/convert",
            params={"amount": str(amount), "from": from_code, "to": to_code},
            headers={},
        )
        result = payload.get("result")
        info = payload.get("info") or {}
        rate = info.get("rate")
        if result is None:
            rates = payload.get("rates") or {}
            rate = rates.get(to_code) or rate
            result = float(amount) * float(rate) if rate is not None else None
        if result is None:
            raise InternetServiceError(f"{to_code} unavailable")
        return float(result), float(rate) if rate is not None else None, payload

    async def _searxng(self, query: str, *, title: str, service: str) -> tuple[str, dict[str, Any], str, None]:
        base_url = settings.searxng_url.strip().rstrip("/")
        if not base_url:
            raise InternetServiceError("SEARXNG_URL is required for keyless search.")
        payload = await self._get(
            f"{base_url}/search",
            params={
                "q": query,
                "format": "json",
                "categories": SEARXNG_CATEGORIES.get(service, "general"),
                "language": "en",
                "safesearch": "1",
            },
            headers={"Accept": "application/json"},
        )
        items = []
        for item in payload.get("results", [])[:5]:
            url = item.get("url") or item.get("img_src") or item.get("thumbnail") or ""
            items.append(
                {
                    "title": item.get("title") or item.get("pretty_url") or "Result",
                    "url": url,
                    "description": item.get("content") or item.get("pretty_url") or "",
                }
            )
        answer = payload.get("answer")
        if not answer and payload.get("infoboxes"):
            answer = payload.get("infoboxes", [{}])[0].get("content")
        return self._format_results(title, query, items, answer=answer), payload, "searxng", None

    async def _brave_search_endpoint(
        self,
        service: str,
        query: str,
        *,
        title: str,
        url: str,
    ) -> tuple[str, dict[str, Any], str, None]:
        if not settings.brave_search_api_key:
            return await self._searxng(query, title=title, service=service)
        payload = await self._get(
            url,
            params={"q": query, "count": "5", "safesearch": "moderate"},
            headers={"X-Subscription-Token": settings.brave_search_api_key, "Accept": "application/json"},
        )
        container = payload.get(service) or payload.get("web") or payload.get("news") or payload.get("images") or {}
        raw_results = container.get("results") if isinstance(container, dict) else None
        items = []
        for item in (raw_results or [])[:5]:
            items.append(
                {
                    "title": item.get("title") or item.get("name") or "Result",
                    "url": item.get("url") or item.get("thumbnail", {}).get("src") or "",
                    "description": item.get("description") or item.get("page_age") or "",
                }
            )
        return self._format_results(title, query, items), payload, "brave", None

    async def _tavily(self, query: str, *, title: str) -> tuple[str, dict[str, Any], str, None]:
        if not settings.tavily_api_key:
            return await self._searxng(query, title=title, service="web")
        payload = await self._post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "search_depth": "basic",
                "include_answer": True,
                "max_results": 5,
            },
            headers={"Content-Type": "application/json"},
        )
        items = [
            {
                "title": item.get("title") or "Result",
                "url": item.get("url") or "",
                "description": item.get("content") or "",
            }
            for item in payload.get("results", [])[:5]
        ]
        answer = payload.get("answer")
        return self._format_results(title, query, items, answer=answer), payload, "tavily", None

    async def _nominatim_geocode(self, location: str) -> list[dict[str, Any]]:
        payload = await self._get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location, "format": "json", "limit": "1"},
            headers={"User-Agent": f"{settings.app_name}/1.0"},
        )
        return payload if isinstance(payload, list) else []

    async def lookup_cache(self, service: str, query: str) -> InternetCache | None:
        stmt = (
            select(InternetCache)
            .where(InternetCache.service == service)
            .where(InternetCache.normalized_query == normalize_text(query))
            .where(InternetCache.expires_at > utcnow())
            .limit(1)
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row:
            row.hit_count += 1
            row.updated_at = utcnow()
            await self.session.flush()
        return row

    async def upsert_cache(self, service: str, query: str, answer: str, payload: dict[str, Any]) -> None:
        ttl = await self.config.get_int("internet_cache_ttl_seconds", settings.internet_cache_ttl_seconds)
        expires_at = utcnow() + timedelta(seconds=max(0, ttl))
        normalized = normalize_text(query)
        row = (
            await self.session.execute(
                select(InternetCache)
                .where(InternetCache.service == service)
                .where(InternetCache.normalized_query == normalized)
                .limit(1)
            )
        ).scalar_one_or_none()
        if row:
            row.answer_text = answer
            row.response_json = payload
            row.expires_at = expires_at
            row.updated_at = utcnow()
            return
        self.session.add(
            InternetCache(
                service=service,
                normalized_query=normalized,
                answer_text=answer,
                response_json=payload,
                expires_at=expires_at,
                updated_at=utcnow(),
            )
        )
        await self.session.flush()

    async def record_usage(
        self,
        contact_id: int | None,
        *,
        service: str,
        query: str,
        provider: str,
        cache_hit: bool,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        self.session.add(
            InternetUsageEvent(
                contact_id=contact_id,
                service=service,
                query_text=query[:1200],
                provider=provider[:40],
                cache_hit=cache_hit,
                success=success,
                error_message=(error_message or "")[:1000] or None,
            )
        )
        await self.session.flush()

    async def check_quota(self, contact_id: int | None) -> dict[str, Any]:
        limit = await self.config.get_int("internet_daily_limit_per_user", settings.internet_daily_limit_per_user)
        if limit <= 0 or not contact_id:
            return {"allowed": True, "limit": limit, "used": 0}
        today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        used = (
            await self.session.execute(
                select(func.count(InternetUsageEvent.id))
                .where(InternetUsageEvent.contact_id == contact_id)
                .where(InternetUsageEvent.created_at >= today_start)
                .where(InternetUsageEvent.cache_hit.is_(False))
                .where(InternetUsageEvent.provider != "disabled")
            )
        ).scalar_one()
        return {"allowed": int(used or 0) < limit, "limit": limit, "used": int(used or 0)}

    async def _enabled_status(self, service: str) -> dict[str, Any]:
        if not await self.config.get_bool("internet_enabled", settings.internet_enabled):
            return {"enabled": False, "reason": "internet_disabled"}
        key = SERVICE_CONFIG_KEYS.get(service)
        default = bool(getattr(settings, SERVICE_SETTING_DEFAULTS.get(service, ""), False))
        if key and not await self.config.get_bool(key, default):
            return {"enabled": False, "reason": f"{service}_disabled"}
        return {"enabled": True, "reason": "enabled"}

    @staticmethod
    def detect_live_service(query: str) -> str | None:
        normalized = normalize_text(query)
        if not normalized:
            return None
        if any(term in normalized for term in ("weather", "temperature", "rain today", "forecast")):
            return "weather"
        if (
            any(term in normalized for term in ("exchange rate", "convert usd", "convert ngn", "currency", " naira ", " dollar "))
            or re.search(r"\b[a-z]{3}\s+(?:to|in)\s+[a-z]{3}\b", normalized)
        ):
            return "currency"
        if any(term in normalized for term in ("latest", "today", "current", "now", "breaking", "news", "this week", "price of", "score")):
            return "web"
        return None

    @staticmethod
    def disabled_message(service: str, *, explicit_command: str | None, reason: str) -> str:
        command = explicit_command or {
            "web": "!search",
            "news": "!news",
            "weather": "!weather",
            "currency": "!currency",
            "youtube": "!youtube",
            "image": "!image",
            "sticker": "!sticker",
            "gif": "!gif",
        }.get(service, "!search")
        owner_hint = "/internet on" if reason == "internet_disabled" else "/internet on"
        return (
            "*Internet Disabled*\n\n"
            f"Use:\n{command} <query>\n\n"
            f"Owner can enable it with:\n{owner_hint}"
        )

    @staticmethod
    def usage_for_command(command: str) -> str:
        examples = {
            "!search": "!search latest OpenAI news",
            "!google": "!google Datacube AU",
            "!news": "!news Nigeria technology",
            "!weather": "!weather Lagos",
            "!currency": "!currency 100 USD to NGN",
            "!youtube": "!youtube Python FastAPI tutorial",
            "!image": "!image Datacube AU logo inspiration",
            "!sticker": "!sticker happy coding",
            "!gif": "!gif celebration",
        }
        return f"Usage:\n{examples.get(command, '!search <query>')}"

    @staticmethod
    def parse_currency(query: str) -> tuple[float, str, str]:
        match = re.search(r"(?:(\d+(?:\.\d+)?)\s*)?([A-Za-z]{3})\s+(?:to|in|=>)\s+([A-Za-z]{3})", query, flags=re.I)
        if not match:
            raise InternetServiceError("Currency format: !currency 100 USD to NGN")
        amount = float(match.group(1) or 1)
        return amount, match.group(2).upper(), match.group(3).upper()

    @staticmethod
    def clean_location_query(query: str) -> str:
        cleaned = normalize_text(query)
        cleaned = re.sub(r"\b(weather|temperature|forecast|rain|today|now|current|in|for|at)\b", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or query.strip()

    @staticmethod
    def weather_code_label(code: Any) -> str:
        labels = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
        }
        try:
            return labels.get(int(code), f"Weather code {code}")
        except (TypeError, ValueError):
            return "Unknown"

    @staticmethod
    def _short_place_name(display_name: str) -> str:
        return ", ".join(part.strip() for part in display_name.split(",")[:3] if part.strip()) or display_name

    @staticmethod
    def _format_results(title: str, query: str, items: list[dict[str, str]], *, answer: str | None = None) -> str:
        lines = [title, "", f"Query:\n{query}"]
        if answer:
            lines.extend(["", "Answer:", answer.strip()])
        if not items:
            lines.extend(["", "No results found."])
            return "\n".join(lines)
        lines.extend(["", "Results:"])
        for index, item in enumerate(items[:5], 1):
            title_text = item.get("title") or "Result"
            url = item.get("url") or ""
            description = item.get("description") or ""
            block = f"{index}. {title_text}"
            if url:
                block += f"\n{url}"
            if description:
                block += f"\n{description[:180]}"
            lines.append(block)
        return "\n\n".join(lines)

    async def _get(self, url: str, *, params: dict[str, str], headers: dict[str, str]) -> Any:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise InternetServiceError(str(exc)) from exc

    async def _post(self, url: str, *, json: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(url, json=json, headers=headers)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise InternetServiceError(str(exc)) from exc


class InternetServiceError(RuntimeError):
    pass
