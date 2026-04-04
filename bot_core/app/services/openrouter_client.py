from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import httpx

from app.config import settings
from app.models.enums import AIMode
from app.utils.hashing import sha256_text


class OpenRouterClientError(RuntimeError):
    pass


@dataclass(slots=True)
class OpenRouterResult:
    text: str
    model: str
    mode: AIMode
    prompt_hash: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    request_json: dict[str, Any]
    response_json: dict[str, Any]


class OpenRouterClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=settings.openrouter_timeout_seconds)

    async def generate(
        self,
        *,
        user_message: str,
        knowledge_context: list[dict[str, object]],
        conversation_summary: str,
        mode: AIMode,
    ) -> OpenRouterResult:
        if not settings.ai_enabled:
            raise OpenRouterClientError("AI is disabled by configuration.")
        if not settings.openrouter_api_key:
            raise OpenRouterClientError("OPENROUTER_API_KEY is required when AI is enabled.")

        model = settings.openrouter_model_light if mode == AIMode.LIGHT else settings.openrouter_model_deep
        context_lines = []
        for idx, chunk in enumerate(knowledge_context[: settings.kb_max_chunks], 1):
            context_lines.append(
                f"[{idx}] {chunk.get('source_type')}/{chunk.get('title')}: {str(chunk.get('content') or '')[:500]}"
            )
        context_blob = "\n".join(context_lines) if context_lines else "No knowledge context."

        system_prompt = (
            "You are the Datacube AU WhatsApp backend assistant. "
            "Keep replies concise, factual, and grounded in provided context."
        )
        user_prompt = (
            f"User message:\n{user_message}\n\n"
            f"Conversation summary:\n{conversation_summary or 'none'}\n\n"
            f"Knowledge context:\n{context_blob}\n\n"
            "If the answer is uncertain, say so briefly. Keep the answer under 120 words."
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        prompt_hash = sha256_text(f"{model}|{system_prompt}|{user_prompt}")
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }

        started = time.perf_counter()
        last_error: Exception | None = None
        for _ in range(settings.openrouter_retry_count + 1):
            try:
                response = await self._client.post(f"{settings.openrouter_base_url}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                usage = data.get("usage", {})
                text = str(data["choices"][0]["message"]["content"]).strip()
                return OpenRouterResult(
                    text=text,
                    model=model,
                    mode=mode,
                    prompt_hash=prompt_hash,
                    prompt_tokens=int(usage.get("prompt_tokens", 0)),
                    completion_tokens=int(usage.get("completion_tokens", 0)),
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    request_json=payload,
                    response_json=data,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc

        assert last_error is not None
        raise OpenRouterClientError(f"OpenRouter request failed: {last_error}") from last_error

    async def close(self) -> None:
        await self._client.aclose()
