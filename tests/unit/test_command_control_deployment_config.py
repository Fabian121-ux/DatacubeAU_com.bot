from pathlib import Path


def test_production_waha_webhook_sends_api_auth_header() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "WAHA_API_KEY: ${WAHA_API_KEY:?Set WAHA_API_KEY in .env.production}" in compose
    assert "WHATSAPP_HOOK_CUSTOM_HEADERS: X-Api-Key:${WAHA_API_KEY:?Set WAHA_API_KEY in .env.production}" in compose
    assert "WHATSAPP_HOOK_URL: ${WHATSAPP_HOOK_URL:-http://api:8080/webhooks/waha-events}" in compose


def test_owner_controls_and_revocations_use_documented_waha_events() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    env_example = Path(".env.example").read_text(encoding="utf-8")

    expected_compose = "WHATSAPP_HOOK_EVENTS: ${WHATSAPP_HOOK_EVENTS:-message,message.any,message.revoked}"
    expected_env = "WHATSAPP_HOOK_EVENTS=message,message.any,message.revoked"
    assert expected_compose in compose
    assert expected_env in env_example
    assert "message.any" in compose
    assert "message.revoked" in compose
