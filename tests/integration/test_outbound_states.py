import pytest
import uuid
from sqlalchemy import select, delete
from datetime import timedelta

from app.workers.background_workers import _deliver_due_outbound_messages, _mark_delivery_failed
from app.models.schema import OutboundMessage
from app.utils.time import utcnow
from app.services.waha_client import WahaClientError
import httpx

class FakeWAHAClient:
    def __init__(self):
        self.sent = []
        self.should_fail_permanent = False
        self.should_fail_transient = False
        
    async def send_text(self, chat_id, text, **kwargs):
        if self.should_fail_permanent:
            response = httpx.Response(status_code=400, text="Bad Request")
            raise WahaClientError("HTTP Error", httpx.HTTPStatusError("HTTP Error", request=httpx.Request("POST", ""), response=response))
        if self.should_fail_transient:
            response = httpx.Response(status_code=500, text="Server Error")
            raise WahaClientError("HTTP Error", httpx.HTTPStatusError("HTTP Error", request=httpx.Request("POST", ""), response=response))
        self.sent.append({"chat_id": chat_id, "text": text})
        return {"id": str(uuid.uuid4())}
        
    async def send_media(self, chat_id, media_url, caption, **kwargs):
        self.sent.append({"chat_id": chat_id, "media": media_url, "caption": caption})
        return {"id": str(uuid.uuid4())}
        
    async def close(self):
        pass


@pytest.mark.asyncio
async def test_deliver_due_messages_success(db_session):
    await db_session.execute(delete(OutboundMessage))
    await db_session.commit()
    
    client = FakeWAHAClient()
    
    msg = OutboundMessage(
        chat_id="123@c.us",
        message_text="Hello success",
        status="queued",
        retry_count=0,
        max_retries=3,
        next_attempt_at=utcnow(),
        updated_at=utcnow()
    )
    db_session.add(msg)
    await db_session.commit()
    
    processed = await _deliver_due_outbound_messages(client)
    assert processed == 1
    assert len(client.sent) == 1
    
    await db_session.refresh(msg)
    assert msg.status == "sent"

@pytest.mark.asyncio
async def test_deliver_due_messages_permanent_fail(db_session):
    await db_session.execute(delete(OutboundMessage))
    await db_session.commit()
    
    client = FakeWAHAClient()
    client.should_fail_permanent = True
    
    msg = OutboundMessage(
        chat_id="123@c.us",
        message_text="Hello fail",
        status="queued",
        retry_count=0,
        max_retries=3,
        next_attempt_at=utcnow(),
        updated_at=utcnow()
    )
    db_session.add(msg)
    await db_session.commit()
    
    processed = await _deliver_due_outbound_messages(client)
    assert processed == 1
    
    await db_session.refresh(msg)
    assert msg.status == "failed_final"
    assert msg.retry_count == 1

@pytest.mark.asyncio
async def test_deliver_due_messages_transient_fail(db_session):
    await db_session.execute(delete(OutboundMessage))
    await db_session.commit()
    
    client = FakeWAHAClient()
    client.should_fail_transient = True
    
    msg = OutboundMessage(
        chat_id="123@c.us",
        message_text="Hello retry",
        status="queued",
        retry_count=0,
        max_retries=3,
        next_attempt_at=utcnow(),
        updated_at=utcnow()
    )
    db_session.add(msg)
    await db_session.commit()
    
    processed = await _deliver_due_outbound_messages(client)
    assert processed == 1
    
    await db_session.refresh(msg)
    assert msg.status == "failed_retryable"
    assert msg.retry_count == 1
    assert msg.next_attempt_at > utcnow()
