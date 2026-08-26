from pathlib import Path


def test_production_waha_webhook_sends_api_auth_header() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "WAHA_API_KEY: ${WAHA_API_KEY:?Set WAHA_API_KEY in .env.production}" in compose
    assert "WHATSAPP_HOOK_CUSTOM_HEADERS: X-Api-Key:${WAHA_API_KEY:?Set WAHA_API_KEY in .env.production}" in compose
    assert "WHATSAPP_HOOK_URL: ${WHATSAPP_HOOK_URL:-http://api:8080/webhooks/waha}" in compose


def test_owner_controls_subscribe_to_message_any_in_documented_defaults() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    env_example = Path(".env.example").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "WHATSAPP_HOOK_EVENTS: ${WHATSAPP_HOOK_EVENTS:-message,message.any}" in compose
    assert "WHATSAPP_HOOK_EVENTS=message,message.any" in env_example
    assert "WHATSAPP_HOOK_EVENTS=message,message.any" in readme
    assert "message.any" in readme
