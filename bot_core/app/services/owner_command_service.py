from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import re
from typing import Any

from sqlalchemy import delete, func, or_, select, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.enums import ChatType, GroupReplyMode, KnowledgeDocumentStatus, SourceType
from app.models.schema import (
    AIUsageEvent,
    AuditLog,
    Contact,
    ConversationSummary,
    ConversationTimeline,
    FAQEntry,
    FeedbackReview,
    ForcedReplyTarget,
    GroupConfig,
    GroupMetadata,
    InternetCache,
    InternetUsageEvent,
    KnowledgeDocument,
    Message,
    OutboundMessage,
    ReplyRule,
    UserMemory,
    UserMemoryTimeline,
    UserTrigger,
)
from app.services.bot_config_service import BotConfigService
from app.services.retrieval_service import RetrievalService
from app.services.waha_client import WAHAClient, WahaClientError
from app.utils.text import normalize_text
from app.utils.time import utcnow


OWNER_ACCESS_DENIED = "⛔ Owner command. Access denied."


@dataclass(slots=True)
class OwnerCommandResult:
    command: str
    reply_text: str
    source_diagnostics: dict[str, Any]


class OwnerCommandService:
    OWNER_COMMANDS = {
        "/remember",
        "/forget",
        "/memory-search",
        "/recent-memory",
        "/teach",
        "/create-command",
        "/edit-command",
        "/delete-command",
        "/groups",
        "/communities",
        "/my-groups",
        "/my-communities",
        "/group-info",
        "/find-group",
        "/inventory",
        "/group-sync",
        "/tag-group",
        "/group-notes",
        "/group-update",
        "/user",
        "/timeline",
        "/summary",
        "/force",
        "/unforce",
        "/trigger",
        "/broadcast",
        "/broadcast-groups",
        "/broadcast-users",
        "/system",
        "/storage",
        "/logs",
        "/errors",
        "/queue",
        "/reviews",
        "/stopbot",
        "/startbot",
        "/maintenance",
        "/mentiononly",
        "/enable-ai",
        "/disable-ai",
        "/top-users",
        "/top-questions",
        "/ai-usage",
        "/memory-stats",
        "/internet",
        "/web",
        "/internet-status",
        "/internet-usage",
        "/owner-help",
    }

    USER_COMMANDS = {"/review", "/whoami"}

    def __init__(self, session: AsyncSession):
        self.session = session
        self.config = BotConfigService(session)
        self.retrieval = RetrievalService(session)

    async def handle(self, message, contact: Contact) -> OwnerCommandResult | None:
        command, args = self.extract_command(message.message_text)
        if not command:
            return None

        if command in self.USER_COMMANDS:
            return await self._handle_user_command(command, args, message, contact)

        if command not in self.OWNER_COMMANDS:
            return None

        is_owner = await self.is_owner_id(message.sender_id)
        if not is_owner:
            await self._audit(
                action="owner_command_denied",
                command=command,
                sender_id=message.sender_id,
                contact_id=contact.id,
                result="denied",
                details={"args_preview": args[:160]},
            )
            return OwnerCommandResult(
                command=command,
                reply_text=OWNER_ACCESS_DENIED,
                source_diagnostics={
                    "source": "Rule",
                    "experience": {"formatted": True},
                    "owner_command": {"command": command, "allowed": False},
                },
            )

        try:
            reply = await self._dispatch(command, args, message, contact)
            result = "ok"
        except ValueError as exc:
            reply = f"*Command Error*\n\n{exc}"
            result = "invalid"

        await self._audit(
            action="owner_command_executed",
            command=command,
            sender_id=message.sender_id,
            contact_id=contact.id,
            result=result,
            details={"args_preview": args[:160]},
        )
        return OwnerCommandResult(
            command=command,
            reply_text=reply,
            source_diagnostics={"source": "Rule", "owner_command": {"command": command, "allowed": True, "result": result}},
        )

    @classmethod
    def extract_command(cls, text_value: str) -> tuple[str | None, str]:
        stripped = text_value.strip()
        if not stripped.startswith("/"):
            return None, ""
        first, _, rest = stripped.partition(" ")
        command = first.strip().lower()
        return command, rest.strip()

    async def is_owner_id(self, sender_id: str) -> bool:
        configured = (await self.config.get("owner_whatsapp_ids", "")).strip() or settings.owner_whatsapp_ids
        return self.is_owner_id_static(sender_id, configured)

    @staticmethod
    def is_owner_id_static(sender_id: str, configured_ids: str) -> bool:
        sender_keys = OwnerCommandService._identity_keys(sender_id)
        owner_keys: set[str] = set()
        for item in re.split(r"[\s,;]+", configured_ids or ""):
            owner_keys.update(OwnerCommandService._identity_keys(item))
        return bool(sender_keys & owner_keys)

    async def _handle_user_command(
        self,
        command: str,
        args: str,
        message,
        contact: Contact,
    ) -> OwnerCommandResult:
        if command == "/review":
            try:
                reply = await self._review(args, message.sender_id, contact.id)
                result = "ok"
            except ValueError as exc:
                reply = f"*Command Error*\n\n{exc}"
                result = "invalid"
            await self._audit(
                action="user_review_created",
                command=command,
                sender_id=message.sender_id,
                contact_id=contact.id,
                result=result,
                details={"args_preview": args[:160]},
            )
            return OwnerCommandResult(
                command=command,
                reply_text=reply,
                source_diagnostics={"source": "Rule", "user_command": {"command": command}},
            )
        if command == "/whoami":
            reply = await self._whoami(message.sender_id)
            await self._audit(
                action="owner_whoami_checked",
                command=command,
                sender_id=message.sender_id,
                contact_id=contact.id,
                result="ok",
                details={},
            )
            return OwnerCommandResult(
                command=command,
                reply_text=reply,
                source_diagnostics={"source": "Rule", "user_command": {"command": command}},
            )
        return OwnerCommandResult(command=command, reply_text="", source_diagnostics={"source": "Rule"})

    async def _dispatch(self, command: str, args: str, message, contact: Contact) -> str:
        handlers = {
            "/remember": self._remember,
            "/forget": self._forget,
            "/memory-search": self._memory_search,
            "/recent-memory": self._recent_memory,
            "/teach": self._teach,
            "/create-command": self._create_command,
            "/edit-command": self._edit_command,
            "/delete-command": self._delete_command,
            "/groups": self._groups,
            "/communities": self._communities,
            "/my-groups": self._my_groups,
            "/my-communities": self._my_communities,
            "/group-info": self._group_info,
            "/find-group": self._find_group,
            "/inventory": self._inventory,
            "/group-sync": self._group_sync,
            "/tag-group": self._tag_group,
            "/group-notes": self._group_notes,
            "/group-update": self._group_update,
            "/user": self._user_profile,
            "/timeline": self._user_timeline,
            "/summary": self._user_summary,
            "/force": self._force,
            "/unforce": self._unforce,
            "/trigger": self._trigger,
            "/broadcast": self._broadcast,
            "/broadcast-groups": self._broadcast_groups,
            "/broadcast-users": self._broadcast_users,
            "/system": self._system,
            "/storage": self._storage,
            "/logs": self._logs,
            "/errors": self._errors,
            "/queue": self._queue,
            "/reviews": self._reviews,
            "/stopbot": self._stopbot,
            "/startbot": self._startbot,
            "/maintenance": self._maintenance,
            "/mentiononly": self._mentiononly,
            "/enable-ai": self._enable_ai,
            "/disable-ai": self._disable_ai,
            "/top-users": self._top_users,
            "/top-questions": self._top_questions,
            "/ai-usage": self._ai_usage,
            "/memory-stats": self._memory_stats,
            "/internet": self._internet_toggle,
            "/web": self._web_toggle,
            "/internet-status": self._internet_status,
            "/internet-usage": self._internet_usage,
            "/owner-help": self._owner_help,
        }
        handler = handlers.get(command)
        if not handler:
            raise ValueError("Unknown owner command.")
        return await handler(args, message, contact)

    async def _whoami(self, sender_id: str) -> str:
        configured = (await self.config.get("owner_whatsapp_ids", "")).strip() or settings.owner_whatsapp_ids
        is_owner = self.is_owner_id_static(sender_id, configured)
        sender_keys = sorted(self._identity_keys(sender_id))
        configured_count = len([item for item in re.split(r"[\s,;]+", configured or "") if item.strip()])
        return (
            "*Who Am I*\n\n"
            f"Detected WhatsApp ID:\n{sender_id or 'unknown'}\n\n"
            f"Owner status:\n{'Owner' if is_owner else 'Not owner'}\n\n"
            f"Permissions:\n{'Owner commands allowed' if is_owner else 'Owner commands denied'}\n\n"
            f"Configured owner entries:\n{configured_count}\n\n"
            "Matching keys checked:\n"
            + "\n".join(f"• {key}" for key in sender_keys[:4])
        )

    async def _owner_help(self, args: str, message, contact: Contact) -> str:
        commands = [
            "/system",
            "/groups",
            "/memory-stats",
            "/internet-status",
            "/whoami",
            "/memory-search <keyword>",
            "/recent-memory",
            "/queue",
            "/logs",
            "/errors",
        ]
        return "*Owner Help*\n\nCommon owner commands:\n\n" + "\n".join(f"• {item}" for item in commands)

    async def _remember(self, args: str, message, contact: Contact) -> str:
        fact = args.strip()
        if not fact:
            raise ValueError("Usage: /remember <approved fact>")
        document = KnowledgeDocument(
            title=f"Owner Memory {utcnow().strftime('%Y-%m-%d %H:%M')}",
            source_type=SourceType.ADMIN_NOTE.value,
            raw_text=fact,
            is_enabled=True,
            status=KnowledgeDocumentStatus.INDEXING.value,
            metadata_json={"owner_approved": True, "created_from": "/remember", "owner_contact_id": contact.id},
            updated_at=utcnow(),
        )
        self.session.add(document)
        await self.session.flush()
        chunks = await self.retrieval.index_document(document)
        return f"*Remembered*\n\nMemory ID:\n{document.id}\n\nChunks:\n{chunks}"

    async def _forget(self, args: str, message, contact: Contact) -> str:
        query = args.strip()
        if not query:
            raise ValueError("Usage: /forget <memory text or keyword>")
        doc_result = await self.session.execute(
            delete(KnowledgeDocument)
            .where(KnowledgeDocument.source_type == SourceType.ADMIN_NOTE.value)
            .where(KnowledgeDocument.raw_text.ilike(f"%{query}%"))
        )
        timeline_result = await self.session.execute(
            delete(UserMemoryTimeline)
            .where(UserMemoryTimeline.source == "owner_command")
            .where(UserMemoryTimeline.memory_text.ilike(f"%{query}%"))
        )
        deleted = (doc_result.rowcount or 0) + (timeline_result.rowcount or 0)
        return f"*Forget Complete*\n\nRemoved:\n{deleted} matching memory item(s)"

    async def _memory_search(self, args: str, message, contact: Contact) -> str:
        query = args.strip()
        if not query:
            raise ValueError("Usage: /memory-search <keyword>")
        docs = (
            await self.session.execute(
                select(KnowledgeDocument)
                .where(KnowledgeDocument.source_type == SourceType.ADMIN_NOTE.value)
                .where(KnowledgeDocument.raw_text.ilike(f"%{query}%"))
                .order_by(KnowledgeDocument.created_at.desc())
                .limit(5)
            )
        ).scalars().all()
        facts = (
            await self.session.execute(
                select(UserMemoryTimeline)
                .where(UserMemoryTimeline.memory_text.ilike(f"%{query}%"))
                .order_by(UserMemoryTimeline.created_at.desc())
                .limit(5)
            )
        ).scalars().all()
        lines = ["*Memory Search*", "", f"Query:\n{query}"]
        for row in docs:
            lines.append(f"• Owner Memory #{row.id}: {self._clip(row.raw_text, 120)}")
        for row in facts:
            lines.append(f"• User Memory #{row.id}: {self._clip(row.memory_text, 120)}")
        if len(lines) == 3:
            lines.append("No matching memories found.")
        return "\n".join(lines)

    async def _recent_memory(self, args: str, message, contact: Contact) -> str:
        docs = (
            await self.session.execute(
                select(KnowledgeDocument)
                .where(KnowledgeDocument.source_type == SourceType.ADMIN_NOTE.value)
                .order_by(KnowledgeDocument.created_at.desc())
                .limit(5)
            )
        ).scalars().all()
        facts = (
            await self.session.execute(
                select(UserMemoryTimeline).order_by(UserMemoryTimeline.created_at.desc()).limit(5)
            )
        ).scalars().all()
        lines = ["*Recent Memory*"]
        for row in docs:
            lines.append(f"• Owner Memory #{row.id}: {self._clip(row.raw_text, 120)}")
        for row in facts:
            lines.append(f"• User Memory #{row.id}: {self._clip(row.memory_text, 120)}")
        if len(lines) == 1:
            lines.append("No recent memory found.")
        return "\n".join(lines)

    async def _teach(self, args: str, message, contact: Contact) -> str:
        blocks = self.parse_label_blocks(args)
        question = blocks.get("question", "").strip()
        answer = blocks.get("answer", "").strip()
        if not question or not answer:
            raise ValueError("Usage: /teach\nQuestion:\n...\nAnswer:\n...")
        normalized = normalize_text(question)
        existing = (
            await self.session.execute(select(FAQEntry).where(FAQEntry.normalized_question == normalized).limit(1))
        ).scalar_one_or_none()
        if existing:
            existing.question = question
            existing.answer = answer
            existing.is_enabled = True
            existing.updated_at = utcnow()
            entry_id = existing.id
            action = "updated"
        else:
            entry = FAQEntry(
                question=question,
                normalized_question=normalized,
                answer=answer,
                is_enabled=True,
                updated_at=utcnow(),
            )
            self.session.add(entry)
            await self.session.flush()
            entry_id = entry.id
            action = "created"
        return f"*FAQ {action.title()}*\n\nFAQ ID:\n{entry_id}\n\nQuestion:\n{question}"

    async def _create_command(self, args: str, message, contact: Contact) -> str:
        blocks = self.parse_label_blocks(args)
        keyword = blocks.get("command", "").strip()
        reply = blocks.get("reply", "").strip()
        if not keyword or not reply:
            raise ValueError("Usage: /create-command\nCommand:\n/scholarship\nReply:\nCheck School Info updates.")
        rule = ReplyRule(
            keyword=keyword,
            response_text=reply,
            match_mode="exact",
            chat_type_filter=None,
            is_enabled=True,
            priority=100,
            updated_at=utcnow(),
        )
        self.session.add(rule)
        await self.session.flush()
        return f"*Custom Command Created*\n\nCommand:\n{keyword}\n\nRule ID:\n{rule.id}"

    async def _edit_command(self, args: str, message, contact: Contact) -> str:
        blocks = self.parse_label_blocks(args)
        keyword = blocks.get("command", "").strip()
        reply = blocks.get("reply", "").strip()
        if not keyword or not reply:
            raise ValueError("Usage: /edit-command\nCommand:\n/scholarship\nReply:\nUpdated reply.")
        rule = await self._find_reply_rule(keyword)
        if not rule:
            raise ValueError(f"Command not found: {keyword}")
        rule.response_text = reply
        rule.updated_at = utcnow()
        return f"*Custom Command Updated*\n\nCommand:\n{keyword}\n\nRule ID:\n{rule.id}"

    async def _delete_command(self, args: str, message, contact: Contact) -> str:
        keyword = args.strip()
        if not keyword:
            blocks = self.parse_label_blocks(args)
            keyword = blocks.get("command", "").strip()
        if not keyword:
            raise ValueError("Usage: /delete-command /scholarship")
        rule = await self._find_reply_rule(keyword)
        if not rule:
            raise ValueError(f"Command not found: {keyword}")
        rule.is_enabled = False
        rule.updated_at = utcnow()
        return f"*Custom Command Disabled*\n\nCommand:\n{keyword}\n\nRule ID:\n{rule.id}"

    async def _groups(self, args: str, message, contact: Contact) -> str:
        groups = await self._known_groups()
        if not groups:
            return "*Groups*\n\nNo known groups yet."
        return "*Groups*\n\n" + "\n\n".join(
            f"{item['name']}\n{item['chat_id']}\nSource: {item.get('source_label', 'Local Owner Metadata')}"
            for item in groups[:20]
        )

    async def _communities(self, args: str, message, contact: Contact) -> str:
        rows = (
            await self.session.execute(
                select(GroupMetadata.community_name, func.count(GroupMetadata.id))
                .where(GroupMetadata.community_name.is_not(None))
                .group_by(GroupMetadata.community_name)
                .order_by(func.count(GroupMetadata.id).desc())
            )
        ).all()
        if not rows:
            return "*Communities*\n\nNo community metadata stored yet.\n\nSource: Local Owner Metadata"
        return "*Communities*\n\n" + "\n\n".join(
            f"{name}\nGroups: {count}\nSource: Local Owner Metadata" for name, count in rows
        )

    async def _my_groups(self, args: str, message, contact: Contact) -> str:
        groups = await self._known_groups()
        if not groups:
            return "*My Groups*\n\nNo known groups yet.\n\nOwner admin status requires WAHA group metadata sync."
        return "*My Groups*\n\n" + "\n\n".join(
            f"{item['name']}\n{item['chat_id']}\nSource: {item.get('source_label', 'Hybrid')}" for item in groups[:20]
        )

    async def _my_communities(self, args: str, message, contact: Contact) -> str:
        return await self._communities(args, message, contact)

    async def _group_info(self, args: str, message, contact: Contact) -> str:
        chat_id = self.clean_target(args)
        if not chat_id:
            raise ValueError("Usage: /group-info <group-id>")
        cfg = (
            await self.session.execute(select(GroupConfig).where(GroupConfig.chat_id == chat_id).limit(1))
        ).scalar_one_or_none()
        message_count = (
            await self.session.execute(select(func.count(Message.id)).where(Message.chat_id == chat_id))
        ).scalar_one()
        metadata = await self._get_group_metadata(chat_id)
        group_name = metadata.group_name if metadata and metadata.group_name else await self._group_name(chat_id)
        member_count = (
            metadata.member_count
            if metadata and metadata.member_count is not None
            else (metadata.participants_count if metadata and metadata.participants_count is not None else None)
        )
        source = self._metadata_source_label(metadata)
        return (
            "*Group Info*\n\n"
            f"Name:\n{group_name}\n\n"
            f"ID:\n{chat_id}\n\n"
            f"Members:\n{member_count if member_count is not None else 'Unavailable'}\n\n"
            f"Description:\n{metadata.description if metadata and metadata.description else 'Unavailable'}\n\n"
            f"Community:\n{metadata.community_name if metadata and metadata.community_name else 'Unavailable'}\n\n"
            f"Bot Status:\n{'Enabled' if not cfg or cfg.is_enabled else 'Disabled'}\n\n"
            f"Reply Mode:\n{cfg.reply_mode if cfg else settings.group_default_reply_mode}\n\n"
            f"Known Messages:\n{message_count}\n\n"
            f"Source:\n{source}"
        )

    async def _find_group(self, args: str, message, contact: Contact) -> str:
        query = args.strip().lower()
        if not query:
            raise ValueError("Usage: /find-group <keyword>")
        groups = [
            item
            for item in await self._known_groups()
            if query in item["name"].lower()
            or query in item["chat_id"].lower()
            or query in normalize_text(str(item.get("tags") or ""))
            or query in normalize_text(str(item.get("purpose") or ""))
        ]
        if not groups:
            return f"*Find Group*\n\nQuery:\n{query}\n\nNo matching groups found."
        return f"*Find Group*\n\nQuery:\n{query}\n\n" + "\n\n".join(
            f"{item['name']}\n{item['chat_id']}\nSource: {item.get('source_label', 'Local Owner Metadata')}" for item in groups[:10]
        )

    async def _inventory(self, args: str, message, contact: Contact) -> str:
        communities = (
            await self.session.execute(
                select(func.count(func.distinct(GroupMetadata.community_name))).where(GroupMetadata.community_name.is_not(None))
            )
        ).scalar_one()
        groups = len(await self._known_groups())
        users = await self._count(Contact)
        memory_entries = await self._count(UserMemoryTimeline)
        faq_entries = await self._count(FAQEntry, FAQEntry.is_enabled.is_(True))
        knowledge_entries = await self._count(KnowledgeDocument, KnowledgeDocument.is_enabled.is_(True))
        bot_enabled = await self.config.get_bool("bot_enabled", True)
        return (
            "*Inventory*\n\n"
            f"Communities:\n{communities}\n\n"
            f"Groups:\n{groups}\n\n"
            f"Known Users:\n{users}\n\n"
            f"Memory Entries:\n{memory_entries}\n\n"
            f"FAQ Entries:\n{faq_entries}\n\n"
            f"Knowledge Entries:\n{knowledge_entries}\n\n"
            f"Bot Status:\n{'Enabled' if bot_enabled else 'Stopped'}\n\n"
            "Source:\nHybrid"
        )

    async def _group_sync(self, args: str, message, contact: Contact) -> str:
        client = WAHAClient()
        try:
            chats = await client.get_chats()
        except WahaClientError as exc:
            return f"*Group Sync*\n\nWAHA metadata unavailable.\n{self._clip(str(exc), 180)}\n\nSource: Local Owner Metadata"
        finally:
            await client.close()

        synced = 0
        for chat in chats:
            payload = self._extract_live_group_payload(chat)
            if not payload:
                continue
            await self._upsert_group_metadata_from_live(payload)
            synced += 1
        return f"*Group Sync*\n\nSynced Groups:\n{synced}\n\nSource:\nLive WAHA"

    async def _tag_group(self, args: str, message, contact: Contact) -> str:
        return await self._save_group_owner_metadata(args, create=True)

    async def _group_update(self, args: str, message, contact: Contact) -> str:
        return await self._save_group_owner_metadata(args, create=False)

    async def _group_notes(self, args: str, message, contact: Contact) -> str:
        chat_id = self.clean_target(args)
        if not chat_id:
            raise ValueError("Usage: /group-notes <group-id>")
        metadata = await self._get_group_metadata(chat_id)
        if not metadata:
            return f"*Group Notes*\n\nNo metadata stored for:\n{chat_id}"
        return "*Group Notes*\n\n" + "\n\n".join(self._group_metadata_payload_lines(metadata))

    async def _user_profile(self, args: str, message, contact: Contact) -> str:
        target = await self._resolve_contact(args)
        if not target:
            raise ValueError("User not found. Usage: /user @user")
        memory = (
            await self.session.execute(select(UserMemory).where(UserMemory.contact_id == target.id).limit(1))
        ).scalar_one_or_none()
        timeline_count = await self._count(ConversationTimeline, ConversationTimeline.contact_id == target.id)
        return (
            f"*User*\n\nName:\n{target.display_name or target.whatsapp_id}\n\n"
            f"WhatsApp:\n{target.whatsapp_id}\n\n"
            f"Relationship:\n{getattr(memory, 'relationship_type', 'unknown') if memory else 'unknown'}\n\n"
            f"Interests:\n{getattr(memory, 'interests', None) or 'None stored'}\n\n"
            f"Goals:\n{getattr(memory, 'goals', None) or 'None stored'}\n\n"
            f"Memory:\n{getattr(memory, 'context_notes', None) or 'None stored'}\n\n"
            f"Timeline Events:\n{timeline_count}"
        )

    async def _user_timeline(self, args: str, message, contact: Contact) -> str:
        target = await self._resolve_contact(args)
        if not target:
            raise ValueError("User not found. Usage: /timeline @user")
        rows = (
            await self.session.execute(
                select(ConversationTimeline)
                .where(ConversationTimeline.contact_id == target.id)
                .order_by(ConversationTimeline.timestamp.desc())
                .limit(8)
            )
        ).scalars().all()
        if not rows:
            return f"*Timeline*\n\nUser:\n{target.display_name or target.whatsapp_id}\n\nNo timeline events stored."
        return f"*Timeline*\n\nUser:\n{target.display_name or target.whatsapp_id}\n\n" + "\n\n".join(
            f"• {row.topic}\n{self._clip(row.summary, 160)}" for row in rows
        )

    async def _user_summary(self, args: str, message, contact: Contact) -> str:
        target = await self._resolve_contact(args)
        if not target:
            raise ValueError("User not found. Usage: /summary @user")
        rows = (
            await self.session.execute(
                select(ConversationSummary)
                .where(ConversationSummary.contact_id == target.id)
                .order_by(ConversationSummary.created_at.desc())
                .limit(5)
            )
        ).scalars().all()
        if not rows:
            return f"*Summary*\n\nUser:\n{target.display_name or target.whatsapp_id}\n\nNo summaries stored."
        return f"*Summary*\n\nUser:\n{target.display_name or target.whatsapp_id}\n\n" + "\n\n".join(
            f"• {self._clip(row.summary, 220)}" for row in rows
        )

    async def _force(self, args: str, message, contact: Contact) -> str:
        target = await self._resolve_contact(args)
        if not target:
            raise ValueError("User not found. Usage: /force @user")
        existing = (
            await self.session.execute(
                select(ForcedReplyTarget).where(ForcedReplyTarget.target_whatsapp_id == target.whatsapp_id).limit(1)
            )
        ).scalar_one_or_none()
        if existing:
            existing.is_enabled = True
            existing.target_contact_id = target.id
            existing.updated_at = utcnow()
        else:
            self.session.add(
                ForcedReplyTarget(
                    target_contact_id=target.id,
                    target_whatsapp_id=target.whatsapp_id,
                    created_by_contact_id=contact.id,
                    is_enabled=True,
                    updated_at=utcnow(),
                )
            )
        return f"*Force Reply*\n\nEnabled for {target.display_name or target.whatsapp_id}."

    async def _unforce(self, args: str, message, contact: Contact) -> str:
        target = await self._resolve_contact(args)
        if not target:
            raise ValueError("User not found. Usage: /unforce @user")
        result = await self.session.execute(
            delete(ForcedReplyTarget).where(ForcedReplyTarget.target_whatsapp_id == target.whatsapp_id)
        )
        return f"*Force Reply*\n\nRemoved:\n{result.rowcount or 0}"

    async def _trigger(self, args: str, message, contact: Contact) -> str:
        target_token, _, body = args.partition("\n")
        target = await self._resolve_contact(target_token.strip())
        if not target:
            raise ValueError("User not found. Usage: /trigger @user\nWhen:\n...\nReply:\n...")
        blocks = self.parse_label_blocks(body)
        when_text = blocks.get("when", "").strip()
        reply = blocks.get("reply", "").strip()
        if not when_text or not reply:
            raise ValueError("Usage: /trigger @user\nWhen:\ngood morning\nReply:\nHave you completed your assignment?")
        trigger = UserTrigger(
            target_contact_id=target.id,
            target_whatsapp_id=target.whatsapp_id,
            trigger_text=when_text,
            normalized_trigger_text=normalize_text(when_text),
            response_text=reply,
            created_by_contact_id=contact.id,
            is_enabled=True,
            updated_at=utcnow(),
        )
        self.session.add(trigger)
        await self.session.flush()
        return f"*User Trigger*\n\nUser:\n{target.display_name or target.whatsapp_id}\n\nTrigger ID:\n{trigger.id}"

    async def _broadcast(self, args: str, message, contact: Contact) -> str:
        text_value = args.strip()
        if not text_value:
            raise ValueError("Usage: /broadcast <message>")
        users = await self._broadcast_user_targets(exclude_whatsapp_id=message.sender_id)
        groups = [item["chat_id"] for item in await self._known_groups()]
        count = await self._queue_broadcast(users + groups, text_value)
        return f"*Broadcast Queued*\n\nTargets:\n{count}"

    async def _broadcast_groups(self, args: str, message, contact: Contact) -> str:
        text_value = args.strip()
        if not text_value:
            raise ValueError("Usage: /broadcast-groups <message>")
        groups = [item["chat_id"] for item in await self._known_groups()]
        count = await self._queue_broadcast(groups, text_value)
        return f"*Group Broadcast Queued*\n\nGroups:\n{count}"

    async def _broadcast_users(self, args: str, message, contact: Contact) -> str:
        text_value = args.strip()
        if not text_value:
            raise ValueError("Usage: /broadcast-users <message>")
        users = await self._broadcast_user_targets(exclude_whatsapp_id=message.sender_id)
        count = await self._queue_broadcast(users, text_value)
        return f"*User Broadcast Queued*\n\nUsers:\n{count}"

    async def _system(self, args: str, message, contact: Contact) -> str:
        bot_enabled = await self.config.get_bool("bot_enabled", True)
        maintenance = await self.config.get_bool("maintenance_mode", False)
        ai_enabled = await self.config.get_bool("ai_enabled", settings.ai_enabled)
        queue_pending = await self._count(OutboundMessage, OutboundMessage.status == "pending")
        memory_count = await self._count(UserMemory)
        waha_status = await self._waha_status()
        return (
            "*System Status*\n\n"
            "API:\nOnline\n\n"
            "Database:\nConnected\n\n"
            f"WAHA:\n{waha_status}\n\n"
            f"Queue:\n{queue_pending} pending\n\n"
            f"Memory:\n{memory_count} profiles\n\n"
            f"AI:\n{'Enabled' if ai_enabled else 'Disabled'}\n\n"
            f"Bot:\n{'Maintenance' if maintenance else ('Enabled' if bot_enabled else 'Stopped')}"
        )

    async def _storage(self, args: str, message, contact: Contact) -> str:
        memory_count = await self._count(UserMemory)
        timeline_count = await self._count(ConversationTimeline)
        knowledge_count = await self._count(KnowledgeDocument)
        faq_count = await self._count(FAQEntry)
        db_size = await self._database_size()
        return (
            "*Storage*\n\n"
            f"Memory Count:\n{memory_count}\n\n"
            f"Timeline Count:\n{timeline_count}\n\n"
            f"Knowledge Count:\n{knowledge_count}\n\n"
            f"FAQ Count:\n{faq_count}\n\n"
            f"Database Size:\n{db_size}"
        )

    async def _logs(self, args: str, message, contact: Contact) -> str:
        rows = (
            await self.session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(8))
        ).scalars().all()
        if not rows:
            return "*Logs*\n\nNo audit logs found."
        return "*Logs*\n\n" + "\n\n".join(f"• {row.action}\n{row.entity_type}:{row.entity_id or '-'}" for row in rows)

    async def _errors(self, args: str, message, contact: Contact) -> str:
        failed_queue = (
            await self.session.execute(
                select(OutboundMessage)
                .where(OutboundMessage.status == "failed")
                .order_by(OutboundMessage.updated_at.desc())
                .limit(5)
            )
        ).scalars().all()
        failed_logs = (
            await self.session.execute(
                select(AuditLog)
                .where(
                    or_(
                        AuditLog.action.ilike("%error%"),
                        AuditLog.action.ilike("%failed%"),
                        AuditLog.action.ilike("%denied%"),
                    )
                )
                .order_by(AuditLog.created_at.desc())
                .limit(5)
            )
        ).scalars().all()
        lines = ["*Errors*"]
        for row in failed_queue:
            lines.append(f"• Queue #{row.id}: {self._clip(row.error_message or row.status, 120)}")
        for row in failed_logs:
            lines.append(f"• Audit #{row.id}: {row.action}")
        if len(lines) == 1:
            lines.append("No recent failures found.")
        return "\n".join(lines)

    async def _queue(self, args: str, message, contact: Contact) -> str:
        counts = await self._queue_counts()
        return (
            "*Queue*\n\n"
            f"Pending:\n{counts.get('pending', 0)}\n\n"
            f"Sending:\n{counts.get('sending', 0)}\n\n"
            f"Failed:\n{counts.get('failed', 0)}\n\n"
            f"Retrying:\n{counts.get('retrying', 0)}"
        )

    async def _review(self, args: str, sender_id: str, contact_id: int) -> str:
        match = re.match(r"^\s*([1-5])(?:\s+(.*))?$", args, flags=re.DOTALL)
        if not match:
            raise ValueError("Usage: /review 5 Great assistant.")
        review = FeedbackReview(
            contact_id=contact_id,
            sender_whatsapp_id=sender_id,
            rating=int(match.group(1)),
            comment=(match.group(2) or "").strip() or None,
        )
        self.session.add(review)
        await self.session.flush()
        return "*Review Saved*\n\nThank you for the feedback."

    async def _reviews(self, args: str, message, contact: Contact) -> str:
        avg_rating = (
            await self.session.execute(select(func.avg(FeedbackReview.rating)))
        ).scalar_one()
        rows = (
            await self.session.execute(select(FeedbackReview).order_by(FeedbackReview.created_at.desc()).limit(5))
        ).scalars().all()
        lines = ["*Reviews*", "", f"Average Rating:\n{round(float(avg_rating or 0), 2)}"]
        if rows:
            lines.append("")
            lines.append("Recent Reviews:")
            for row in rows:
                lines.append(f"• {row.rating}/5 {self._clip(row.comment or '', 120)}".rstrip())
        else:
            lines.extend(["", "No reviews yet."])
        return "\n".join(lines)

    async def _stopbot(self, args: str, message, contact: Contact) -> str:
        await self.config.set("bot_enabled", "false")
        await self.config.set("maintenance_mode", "false")
        return "*Bot Control*\n\nBot stopped.\n\nOwner commands remain available."

    async def _startbot(self, args: str, message, contact: Contact) -> str:
        await self.config.set("bot_enabled", "true")
        await self.config.set("maintenance_mode", "false")
        return "*Bot Control*\n\nBot started."

    async def _maintenance(self, args: str, message, contact: Contact) -> str:
        await self.config.set("maintenance_mode", "true")
        return "*Maintenance*\n\nMaintenance mode enabled.\n\nNormal replies are paused."

    async def _mentiononly(self, args: str, message, contact: Contact) -> str:
        await self.config.set("group_default_reply_mode", GroupReplyMode.MENTION_ONLY.value)
        result = await self.session.execute(select(GroupConfig))
        rows = result.scalars().all()
        for row in rows:
            row.reply_mode = GroupReplyMode.MENTION_ONLY.value
            row.updated_at = utcnow()
        return f"*Mention Only*\n\nMention-only mode enabled.\n\nUpdated configured groups:\n{len(rows)}"

    async def _enable_ai(self, args: str, message, contact: Contact) -> str:
        await self.config.set("ai_enabled", "true")
        return "*AI Control*\n\nAI enabled."

    async def _disable_ai(self, args: str, message, contact: Contact) -> str:
        await self.config.set("ai_enabled", "false")
        return "*AI Control*\n\nAI disabled."

    async def _top_users(self, args: str, message, contact: Contact) -> str:
        rows = (
            await self.session.execute(
                select(Contact.display_name, Contact.whatsapp_id, func.count(Message.id))
                .join(Message, Message.contact_id == Contact.id)
                .where(Message.chat_type == ChatType.DM.value)
                .group_by(Contact.id)
                .order_by(func.count(Message.id).desc())
                .limit(10)
            )
        ).all()
        if not rows:
            return "*Top Users*\n\nNo user activity yet."
        return "*Top Users*\n\n" + "\n".join(f"• {name or wa}: {count}" for name, wa, count in rows)

    async def _top_questions(self, args: str, message, contact: Contact) -> str:
        rows = (
            await self.session.execute(
                select(Message.normalized_text, func.count(Message.id))
                .where(Message.message_text != "")
                .where(Message.normalized_text != "")
                .group_by(Message.normalized_text)
                .order_by(func.count(Message.id).desc())
                .limit(10)
            )
        ).all()
        if not rows:
            return "*Top Questions*\n\nNo questions recorded yet."
        return "*Top Questions*\n\n" + "\n".join(f"• {self._clip(text_value, 80)}: {count}" for text_value, count in rows)

    async def _ai_usage(self, args: str, message, contact: Contact) -> str:
        now = utcnow()
        daily = await self._token_usage_since(now - timedelta(days=1))
        weekly = await self._token_usage_since(now - timedelta(days=7))
        monthly = await self._token_usage_since(now - timedelta(days=30))
        return (
            "*AI Usage*\n\n"
            f"Daily:\n{daily['calls']} calls, {daily['tokens']} tokens\n\n"
            f"Weekly:\n{weekly['calls']} calls, {weekly['tokens']} tokens\n\n"
            f"Monthly:\n{monthly['calls']} calls, {monthly['tokens']} tokens"
        )

    async def _memory_stats(self, args: str, message, contact: Contact) -> str:
        profiles = await self._count(UserMemory)
        timeline = await self._count(ConversationTimeline)
        summaries = await self._count(ConversationSummary)
        knowledge = await self._count(KnowledgeDocument)
        return (
            "*Memory Stats*\n\n"
            f"Profiles:\n{profiles}\n\n"
            f"Timeline Entries:\n{timeline}\n\n"
            f"Summaries:\n{summaries}\n\n"
            f"Knowledge Growth:\n{knowledge} documents"
        )

    async def _internet_toggle(self, args: str, message, contact: Contact) -> str:
        value = normalize_text(args)
        if value not in {"on", "off"}:
            raise ValueError("Usage: /internet on or /internet off")
        enabled = value == "on"
        await self.config.set("internet_enabled", str(enabled).lower())
        for key in (
            "web_search_enabled",
            "news_enabled",
            "weather_enabled",
            "currency_enabled",
            "youtube_enabled",
            "image_search_enabled",
            "sticker_search_enabled",
        ):
            await self.config.set(key, str(enabled).lower())
        return f"*Internet*\n\nServices are now {'enabled' if enabled else 'disabled'}."

    async def _web_toggle(self, args: str, message, contact: Contact) -> str:
        value = normalize_text(args)
        if value not in {"on", "off"}:
            raise ValueError("Usage: /web on or /web off")
        enabled = value == "on"
        if enabled:
            await self.config.set("internet_enabled", "true")
        await self.config.set("web_search_enabled", str(enabled).lower())
        return f"*Web Search*\n\nWeb search is now {'enabled' if enabled else 'disabled'}."

    async def _internet_status(self, args: str, message, contact: Contact) -> str:
        keys = [
            ("Internet", "internet_enabled"),
            ("Web Search", "web_search_enabled"),
            ("News", "news_enabled"),
            ("Weather", "weather_enabled"),
            ("Currency", "currency_enabled"),
            ("YouTube", "youtube_enabled"),
            ("Image Search", "image_search_enabled"),
            ("Sticker Search", "sticker_search_enabled"),
        ]
        provider = await self.config.get("internet_provider", settings.internet_provider)
        cache_count = await self._count(InternetCache)
        lines = ["*Internet Status*", "", f"Provider:\n{provider}", "", f"Cache Entries:\n{cache_count}", "", "Services:"]
        for label, key in keys:
            lines.append(f"• {label}: {'On' if await self.config.get_bool(key, False) else 'Off'}")
        lines.extend(
            [
                "",
                "Providers:",
                f"• SearXNG: {settings.searxng_url or 'Missing SEARXNG_URL'}",
                f"• Brave: {'Configured' if bool(settings.brave_search_api_key) else 'Optional'}",
                f"• Tavily: {'Configured' if bool(settings.tavily_api_key) else 'Optional'}",
                "• Weather: Open-Meteo + Nominatim",
                "• Currency: Frankfurter + exchangerate.host",
                f"• YouTube: {'Configured' if bool(settings.youtube_api_key) else 'Optional/Missing'}",
                f"• Giphy: {'Configured' if bool(settings.giphy_api_key) else 'Optional/Missing'}",
            ]
        )
        return "\n".join(lines)

    async def _internet_usage(self, args: str, message, contact: Contact) -> str:
        today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today_start.replace(day=1)
        today = await self._internet_usage_totals(today_start)
        month = await self._internet_usage_totals(month_start)
        top_rows = (
            await self.session.execute(
                select(InternetUsageEvent.service, func.count(InternetUsageEvent.id))
                .where(InternetUsageEvent.created_at >= month_start)
                .group_by(InternetUsageEvent.service)
                .order_by(func.count(InternetUsageEvent.id).desc())
                .limit(8)
            )
        ).all()
        lines = [
            "*Internet Usage*",
            "",
            f"Today:\n{today['requests']} requests, {today['cache_hits']} cache hits",
            "",
            f"Month:\n{month['requests']} requests, {month['cache_hits']} cache hits",
        ]
        if top_rows:
            lines.extend(["", "Top Services:"])
            for service, count in top_rows:
                lines.append(f"• {service}: {count}")
        return "\n".join(lines)

    async def _find_reply_rule(self, keyword: str) -> ReplyRule | None:
        normalized = normalize_text(keyword)
        rows = (await self.session.execute(select(ReplyRule))).scalars().all()
        for row in rows:
            if normalize_text(row.keyword) == normalized:
                return row
        return None

    async def _save_group_owner_metadata(self, args: str, *, create: bool) -> str:
        first, _, body = args.partition("\n")
        group_id = self.clean_target(first)
        if not group_id:
            raise ValueError("Usage: /tag-group <group-id>\ncommunity_name=...\nowner_name=...\npurpose=...\ntags=a,b")
        values = self.parse_key_values(body or args.replace(first, "", 1))
        if not values:
            raise ValueError("Provide metadata as key=value lines.")
        metadata = await self._get_group_metadata(group_id)
        if not metadata:
            if not create:
                raise ValueError(f"No metadata found for {group_id}. Use /tag-group first.")
            metadata = GroupMetadata(chat_id=group_id, source="local", updated_at=utcnow())
            self.session.add(metadata)
            await self.session.flush()
        for key in ("group_name", "community_name", "owner_name", "purpose", "notes", "description"):
            if key in values:
                setattr(metadata, key, values[key][:2000] if key in {"purpose", "notes", "description"} else values[key][:220])
        if "tags" in values:
            metadata.tags = [item.strip() for item in re.split(r"[,;]", values["tags"]) if item.strip()][:20]
        if "member_count" in values:
            metadata.member_count = self._int_or_none(values["member_count"])
        metadata.source = "hybrid" if metadata.live_metadata_json else "local"
        metadata.updated_at = utcnow()
        await self.session.flush()
        action = "stored" if create else "updated"
        return f"*Group Metadata {action.title()}*\n\nGroup:\n{group_id}\n\nSource:\n{self._metadata_source_label(metadata)}"

    async def _get_group_metadata(self, chat_id: str) -> GroupMetadata | None:
        return (
            await self.session.execute(select(GroupMetadata).where(GroupMetadata.chat_id == chat_id).limit(1))
        ).scalar_one_or_none()

    async def _upsert_group_metadata_from_live(self, payload: dict[str, Any]) -> GroupMetadata:
        chat_id = payload["chat_id"]
        metadata = await self._get_group_metadata(chat_id)
        if not metadata:
            metadata = GroupMetadata(chat_id=chat_id, first_seen=utcnow(), source="live", updated_at=utcnow())
            self.session.add(metadata)
            await self.session.flush()
        metadata.group_name = payload.get("group_name") or metadata.group_name
        metadata.member_count = payload.get("member_count") if payload.get("member_count") is not None else metadata.member_count
        metadata.participants_count = (
            payload.get("participants_count") if payload.get("participants_count") is not None else metadata.participants_count
        )
        metadata.description = payload.get("description") or metadata.description
        metadata.bot_present = payload.get("bot_present") if payload.get("bot_present") is not None else metadata.bot_present
        metadata.last_seen = utcnow()
        metadata.live_metadata_json = payload.get("raw") or {}
        metadata.source = "hybrid" if any([metadata.community_name, metadata.owner_name, metadata.purpose, metadata.notes, metadata.tags]) else "live"
        metadata.updated_at = utcnow()
        await self.session.flush()
        return metadata

    def _extract_live_group_payload(self, chat: dict[str, Any]) -> dict[str, Any] | None:
        chat_id = str(chat.get("id") or chat.get("chatId") or chat.get("_id") or "").strip()
        if isinstance(chat.get("id"), dict):
            chat_id = str(chat["id"].get("_serialized") or chat["id"].get("user") or "").strip()
        if not chat_id or ("@g.us" not in chat_id and not chat.get("isGroup")):
            return None
        participants = chat.get("participants")
        participants_count = len(participants) if isinstance(participants, list) else None
        return {
            "chat_id": chat_id,
            "group_name": chat.get("name") or chat.get("subject") or chat.get("formattedTitle") or chat.get("title"),
            "member_count": self._int_or_none(chat.get("membersCount") or chat.get("participantsCount") or chat.get("size")),
            "participants_count": participants_count,
            "description": chat.get("description") or chat.get("desc"),
            "bot_present": self._bot_present_in_payload(chat),
            "raw": chat,
        }

    @staticmethod
    def _bot_present_in_payload(chat: dict[str, Any]) -> bool | None:
        participants = chat.get("participants")
        bot_number = settings.bot_wa_number
        if not isinstance(participants, list) or not bot_number:
            return None
        bot_keys = OwnerCommandService._identity_keys(bot_number)
        for participant in participants:
            value = participant.get("id") if isinstance(participant, dict) else participant
            if OwnerCommandService._identity_keys(str(value)) & bot_keys:
                return True
        return False

    @staticmethod
    def _metadata_source_label(metadata: GroupMetadata | None) -> str:
        if not metadata:
            return "Local Owner Metadata"
        if metadata.source == "live":
            return "Live WAHA"
        if metadata.source == "hybrid":
            return "Hybrid"
        return "Local Owner Metadata"

    def _group_metadata_payload_lines(self, metadata: GroupMetadata) -> list[str]:
        tags = ", ".join(metadata.tags or [])
        return [
            f"Name:\n{metadata.group_name or 'Unknown'}",
            f"ID:\n{metadata.chat_id}",
            f"Community:\n{metadata.community_name or 'None stored'}",
            f"Owner:\n{metadata.owner_name or 'None stored'}",
            f"Purpose:\n{metadata.purpose or 'None stored'}",
            f"Notes:\n{metadata.notes or 'None stored'}",
            f"Tags:\n{tags or 'None stored'}",
            f"Members:\n{metadata.member_count if metadata.member_count is not None else 'Unavailable'}",
            f"Description:\n{metadata.description or 'Unavailable'}",
            f"Source:\n{self._metadata_source_label(metadata)}",
        ]

    async def _resolve_contact(self, target: str) -> Contact | None:
        clean = self.clean_target(target)
        if not clean:
            return None
        keys = self._identity_keys(clean)
        conditions = [Contact.display_name.ilike(f"%{clean.lstrip('@')}%")]
        for key in keys:
            conditions.append(Contact.whatsapp_id == key)
            conditions.append(Contact.whatsapp_id.ilike(f"%{key}%"))
        return (
            await self.session.execute(select(Contact).where(or_(*conditions)).order_by(Contact.updated_at.desc()).limit(1))
        ).scalar_one_or_none()

    async def _known_groups(self) -> list[dict[str, Any]]:
        chat_ids = set(
            (
                await self.session.execute(
                    select(Message.chat_id).where(Message.chat_type == ChatType.GROUP.value).distinct()
                )
            ).scalars().all()
        )
        chat_ids.update((await self.session.execute(select(GroupConfig.chat_id))).scalars().all())
        metadata_rows = (await self.session.execute(select(GroupMetadata))).scalars().all()
        metadata_by_id = {row.chat_id: row for row in metadata_rows}
        chat_ids.update(metadata_by_id)
        groups: list[dict[str, Any]] = []
        for chat_id in sorted(chat_ids):
            metadata = metadata_by_id.get(chat_id)
            groups.append(
                {
                    "chat_id": chat_id,
                    "name": metadata.group_name if metadata and metadata.group_name else await self._group_name(chat_id),
                    "source_label": self._metadata_source_label(metadata),
                    "tags": metadata.tags if metadata else [],
                    "purpose": metadata.purpose if metadata else "",
                }
            )
        return groups

    async def _group_name(self, chat_id: str) -> str:
        payload = (
            await self.session.execute(
                select(Message.raw_payload_json).where(Message.chat_id == chat_id).order_by(Message.created_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        if isinstance(payload, dict):
            for path in (("chat", "name"), ("group", "name")):
                current: Any = payload
                for key in path:
                    current = current.get(key) if isinstance(current, dict) else None
                if current:
                    return str(current)
            for key in ("chatName", "groupName", "name"):
                if payload.get(key):
                    return str(payload[key])
        return "Known Group"

    async def _broadcast_user_targets(self, *, exclude_whatsapp_id: str) -> list[str]:
        rows = (await self.session.execute(select(Contact.whatsapp_id))).scalars().all()
        exclude = self._identity_keys(exclude_whatsapp_id)
        return [row for row in rows if not (self._identity_keys(row) & exclude)]

    async def _queue_broadcast(self, targets: list[str], text_value: str) -> int:
        unique_targets = list(dict.fromkeys(target for target in targets if target))
        for chat_id in unique_targets:
            self.session.add(
                OutboundMessage(
                    chat_id=chat_id,
                    message_text=text_value,
                    status="pending",
                    retry_count=0,
                    max_retries=3,
                    next_attempt_at=utcnow(),
                    updated_at=utcnow(),
                )
            )
        await self.session.flush()
        return len(unique_targets)

    async def _count(self, model, *conditions) -> int:
        stmt = select(func.count(model.id))
        for condition in conditions:
            stmt = stmt.where(condition)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _queue_counts(self) -> dict[str, int]:
        rows = (
            await self.session.execute(select(OutboundMessage.status, func.count(OutboundMessage.id)).group_by(OutboundMessage.status))
        ).all()
        return {str(status): int(count) for status, count in rows}

    async def _token_usage_since(self, since) -> dict[str, int]:
        row = (
            await self.session.execute(
                select(func.count(AIUsageEvent.id), func.coalesce(func.sum(AIUsageEvent.total_tokens), 0))
                .where(AIUsageEvent.created_at >= since)
            )
        ).one()
        return {"calls": int(row[0] or 0), "tokens": int(row[1] or 0)}

    async def _internet_usage_totals(self, since) -> dict[str, int]:
        requests = (
            await self.session.execute(
                select(func.count(InternetUsageEvent.id)).where(InternetUsageEvent.created_at >= since)
            )
        ).scalar_one()
        cache_hits = (
            await self.session.execute(
                select(func.count(InternetUsageEvent.id))
                .where(InternetUsageEvent.created_at >= since)
                .where(InternetUsageEvent.cache_hit.is_(True))
            )
        ).scalar_one()
        return {"requests": int(requests or 0), "cache_hits": int(cache_hits or 0)}

    async def _waha_status(self) -> str:
        client = WAHAClient()
        try:
            status = await client.get_session_status()
            return str(status.get("status") or status.get("state") or "Unknown")
        except WahaClientError as exc:
            return f"Unavailable: {self._clip(str(exc), 80)}"
        finally:
            await client.close()

    async def _database_size(self) -> str:
        try:
            return str((await self.session.execute(sql_text("SELECT pg_size_pretty(pg_database_size(current_database()))"))).scalar_one())
        except Exception:  # noqa: BLE001
            return "Unavailable"

    async def _audit(
        self,
        *,
        action: str,
        command: str,
        sender_id: str,
        contact_id: int | None,
        result: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = dict(details or {})
        payload.update({"sender_id": sender_id, "contact_id": contact_id, "result": result})
        self.session.add(
            AuditLog(
                action=action,
                entity_type="owner_command",
                entity_id=command,
                details_json=payload,
            )
        )
        await self.session.flush()

    @staticmethod
    def parse_label_blocks(text_value: str) -> dict[str, str]:
        blocks: dict[str, list[str]] = {}
        current: str | None = None
        for raw_line in text_value.splitlines():
            match = re.match(r"^\s*([A-Za-z][A-Za-z\s_-]{0,40}):\s*(.*)$", raw_line)
            if match:
                current = normalize_text(match.group(1)).replace(" ", "_")
                blocks.setdefault(current, [])
                if match.group(2).strip():
                    blocks[current].append(match.group(2).strip())
                continue
            if current:
                blocks[current].append(raw_line.rstrip())
        aliases = {
            "q": "question",
            "a": "answer",
            "response": "reply",
        }
        result = {key: "\n".join(lines).strip() for key, lines in blocks.items()}
        for alias, canonical in aliases.items():
            if alias in result and canonical not in result:
                result[canonical] = result[alias]
        return result

    @staticmethod
    def parse_key_values(text_value: str) -> dict[str, str]:
        values: dict[str, str] = {}
        for raw_line in text_value.splitlines():
            if "=" not in raw_line:
                continue
            key, value = raw_line.split("=", 1)
            normalized_key = normalize_text(key).replace(" ", "_")
            cleaned_value = value.strip()
            if normalized_key and cleaned_value:
                values[normalized_key] = cleaned_value
        return values

    @staticmethod
    def clean_target(value: str) -> str:
        raw = value.strip()
        mailto_match = re.search(r"mailto:([^)>\s]+)", raw, flags=re.IGNORECASE)
        if mailto_match:
            return mailto_match.group(1).strip()
        whatsapp_match = re.search(r"([A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+)", raw)
        if whatsapp_match:
            return whatsapp_match.group(1).strip()
        cleaned = raw
        cleaned = re.sub(r"^mailto:", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip("[]()<>")
        if cleaned.startswith("@"):
            cleaned = cleaned[1:]
        return cleaned.strip()

    @staticmethod
    def _identity_keys(value: str) -> set[str]:
        cleaned = OwnerCommandService.clean_target(str(value or "").lower())
        if not cleaned:
            return set()
        keys = {cleaned}
        if "@" in cleaned:
            keys.add(cleaned.split("@", 1)[0])
        else:
            keys.add(f"{cleaned}@c.us")
        digits = re.sub(r"\D+", "", cleaned)
        if digits:
            keys.add(digits)
            keys.add(f"{digits}@c.us")
        return keys

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clip(value: str, limit: int) -> str:
        cleaned = re.sub(r"\s+", " ", value or "").strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[:limit].rstrip() + "..."
