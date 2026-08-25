from pathlib import Path


def test_production_waha_webhook_sends_api_auth_header() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "WHATSAPP_HOOK_CUSTOM_HEADERS: X-Api-Key:${WAHA_API_KEY}" in compose
    assert "WHATSAPP_HOOK_URL: ${WHATSAPP_HOOK_URL:-http://api:8080/webhooks/waha}" in compose
