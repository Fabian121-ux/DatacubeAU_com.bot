from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Base
import app.models.schema  # noqa: F401 - imports mapped models into Base.metadata


EXPECTED_INDEXES = {
    "idx_messages_chat_created",
    "idx_messages_contact_created",
    "idx_messages_direction_created",
    "idx_messages_normalized_text",
    "idx_router_decisions_message_created",
    "idx_group_configs_chat_id",
    "idx_dm_configs_contact_id",
    "idx_knowledge_documents_status_enabled",
    "idx_knowledge_chunks_document_id",
    "idx_qa_cache_normalized_question",
    "idx_ai_calls_message_created",
    "idx_conversation_sessions_chat_id",
    "idx_audit_logs_created",
    "idx_reply_rules_enabled_priority",
    "idx_user_memory_contact",
    "idx_bot_config_key",
    "idx_user_memory_timeline_contact",
    "idx_faq_entries_normalized",
    "idx_outbound_queue_status_attempt",
    "idx_user_memory_relationship_type",
    "idx_user_memory_last_interaction",
    "idx_conversation_timeline_contact_time",
    "idx_conversation_timeline_contact_importance",
    "idx_conversation_summaries_contact_time",
    "idx_conversation_summaries_contact_threshold",
    "idx_ai_usage_quotas_reset",
    "idx_ai_usage_events_contact_time",
    "idx_ai_usage_events_created_at",
    "idx_forced_reply_targets_contact",
    "idx_forced_reply_targets_whatsapp",
    "idx_user_triggers_contact",
    "idx_user_triggers_whatsapp",
    "idx_feedback_reviews_created_at",
    "idx_feedback_reviews_contact",
    "idx_internet_cache_expiry",
    "idx_internet_cache_service_query",
    "idx_internet_usage_contact_time",
    "idx_internet_usage_service_time",
    "idx_group_metadata_chat_id",
    "idx_group_metadata_community",
    "idx_group_metadata_source",
}

EXPECTED_CONSTRAINTS = {
    "router_decisions_decision_type_check",
    "user_memory_relationship_type_check",
}

IGNORED_TABLES = {"schema_migrations"}


@dataclass(slots=True)
class AuditSnapshot:
    tables: set[str]
    columns: dict[str, dict[str, dict[str, Any]]]
    indexes: set[str]
    constraints: set[str]


def database_url() -> str:
    value = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_SYNC")
    if not value:
        raise RuntimeError("DATABASE_URL or DATABASE_URL_SYNC is required for schema audit.")
    if value.startswith("postgresql+asyncpg://"):
        return value
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+asyncpg://", 1)
    raise RuntimeError("schema audit only supports PostgreSQL URLs.")


def expected_type_name(column_type: Any) -> str:
    raw = column_type.__class__.__name__.lower()
    if raw == "biginteger":
        return "bigint"
    if raw == "integer":
        return "integer"
    if raw == "string":
        return "character varying"
    if raw == "text":
        return "text"
    if raw == "boolean":
        return "boolean"
    if raw == "datetime":
        return "timestamp with time zone"
    if raw == "float":
        return "double precision"
    if raw == "json":
        return "json"
    return raw


def compatible_type(expected: str, actual: str) -> bool:
    if expected == actual:
        return True
    if expected == "character varying" and (actual.startswith("character varying") or actual.startswith("varchar")):
        return True
    if expected == "json" and actual in {"json", "jsonb"}:
        return True
    if expected == "timestamp with time zone" and actual.startswith("timestamp"):
        return True
    return False


def collect_snapshot(sync_connection) -> AuditSnapshot:
    inspector = inspect(sync_connection)
    tables = set(inspector.get_table_names(schema="public"))
    columns: dict[str, dict[str, dict[str, Any]]] = {}
    indexes: set[str] = set()
    constraints: set[str] = set()

    for table in tables:
        columns[table] = {
            column["name"]: {
                "type": str(column["type"]).lower(),
                "nullable": bool(column["nullable"]),
            }
            for column in inspector.get_columns(table, schema="public")
        }
        indexes.update(index["name"] for index in inspector.get_indexes(table, schema="public"))
        constraints.update(constraint["name"] for constraint in inspector.get_unique_constraints(table, schema="public"))
        constraints.update(constraint["name"] for constraint in inspector.get_foreign_keys(table, schema="public"))
        pk = inspector.get_pk_constraint(table, schema="public")
        if pk.get("name"):
            constraints.add(pk["name"])

    check_rows = sync_connection.exec_driver_sql(
        """
        SELECT conname
        FROM pg_constraint
        WHERE connamespace = 'public'::regnamespace
          AND contype = 'c'
        """
    ).fetchall()
    constraints.update(str(row[0]) for row in check_rows)
    return AuditSnapshot(tables=tables, columns=columns, indexes=indexes, constraints=constraints)


def audit(snapshot: AuditSnapshot) -> list[str]:
    problems: list[str] = []
    metadata = Base.metadata

    for table_name, table in sorted(metadata.tables.items()):
        if table_name in IGNORED_TABLES:
            continue
        if table_name not in snapshot.tables:
            problems.append(f"missing table: {table_name}")
            continue
        actual_columns = snapshot.columns.get(table_name, {})
        for column in table.columns:
            if column.name not in actual_columns:
                problems.append(f"missing column: {table_name}.{column.name}")
                continue
            expected_type = expected_type_name(column.type)
            actual_type = actual_columns[column.name]["type"]
            if not compatible_type(expected_type, actual_type):
                problems.append(
                    f"type mismatch: {table_name}.{column.name} expected {expected_type}, got {actual_type}"
                )
            if not column.nullable and actual_columns[column.name]["nullable"]:
                problems.append(f"nullable mismatch: {table_name}.{column.name} should be NOT NULL")

    for index_name in sorted(EXPECTED_INDEXES):
        if index_name not in snapshot.indexes:
            problems.append(f"missing index: {index_name}")

    for constraint_name in sorted(EXPECTED_CONSTRAINTS):
        if constraint_name not in snapshot.constraints:
            problems.append(f"missing constraint: {constraint_name}")

    return problems


async def main() -> int:
    engine = create_async_engine(database_url(), pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            snapshot = await connection.run_sync(collect_snapshot)
        problems = audit(snapshot)
        if problems:
            print("Schema audit failed:")
            for problem in problems:
                print(f"- {problem}")
            return 1
        print("Schema audit passed.")
        print(f"Tables checked: {len(Base.metadata.tables)}")
        print(f"Indexes checked: {len(EXPECTED_INDEXES)}")
        print(f"Constraints checked: {len(EXPECTED_CONSTRAINTS)}")
        return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
