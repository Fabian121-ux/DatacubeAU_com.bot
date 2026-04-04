from enum import StrEnum


class ChatType(StrEnum):
    DM = "dm"
    GROUP = "group"


class Direction(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    OTHER = "other"


class SourceType(StrEnum):
    ARCHITECTURE = "architecture"
    BRANCH_NOTES = "branch_notes"
    PRODUCT_DOCS = "product_docs"
    FAQ = "faq"
    SUPPORT_FIX = "support_fix"
    PRICING = "pricing"
    POLICY = "policy"
    CHAT_SUMMARY = "chat_summary"
    ADMIN_NOTE = "admin_note"


class KnowledgeDocumentStatus(StrEnum):
    ACTIVE = "active"
    INDEXING = "indexing"
    ERROR = "error"
    DISABLED = "disabled"


class GroupReplyMode(StrEnum):
    MENTION_ONLY = "mention_only"
    OFF = "off"


class DecisionType(StrEnum):
    IGNORE = "ignore"
    STATIC_REPLY = "static_reply"
    KB_REPLY = "kb_reply"
    COOLDOWN_BLOCK = "cooldown_block"
    NO_MATCH = "no_match"
    AI_REPLY_LIGHT = "ai_reply_light"
    AI_REPLY_DEEP = "ai_reply_deep"


class AIMode(StrEnum):
    LIGHT = "light"
    DEEP = "deep"


class SessionStatus(StrEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    STARTING = "starting"
    QR_REQUIRED = "qr_required"
    UNKNOWN = "unknown"
