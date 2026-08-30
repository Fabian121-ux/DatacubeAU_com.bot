from app.models.schema import OutboundMessage
from app.workers import background_workers


def _message(*, chat_id: str, formatting_json: dict | None) -> OutboundMessage:
    return OutboundMessage(
        chat_id=chat_id,
        message_text="hello",
        formatting_json=formatting_json,
        status="pending",
        retry_count=0,
        max_retries=3,
    )


def test_immediate_router_reply_to_external_contact_fails_closed(monkeypatch):
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    message = _message(
        chat_id="222@c.us",
        formatting_json={"delivery_policy": "immediate"},
    )

    assert background_workers._delivery_authorized(message) is False


def test_immediate_router_reply_to_exact_owner_chat_remains_authorized(monkeypatch):
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us,333@c.us")
    message = _message(
        chat_id="333@c.us",
        formatting_json={"delivery_policy": "immediate"},
    )

    assert background_workers._delivery_authorized(message) is True


def test_owner_push_and_other_non_router_queue_paths_are_not_reclassified(monkeypatch):
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    message = _message(
        chat_id="111@c.us",
        formatting_json={"source": "owner_push", "command": ".push"},
    )

    assert background_workers._delivery_authorized(message) is True


def test_deferred_router_reply_never_becomes_authorized_by_fence(monkeypatch):
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    message = _message(
        chat_id="222@c.us",
        formatting_json={"delivery_policy": "wait_for_fabian_first"},
    )

    # Deferred rows are not selected by the delivery query; this helper does not
    # reinterpret their status as authorization or promote them to pending.
    assert message.status == "pending"
    assert background_workers._delivery_authorized(message) is True
