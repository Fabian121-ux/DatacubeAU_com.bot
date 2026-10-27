from __future__ import annotations

from typing import Any


def _positive_hit_count(value: Any) -> bool:
    try:
        return float(value or 0) > 0
    except (TypeError, ValueError):
        return bool(value)


def internet_used_from_diagnostics(source_diagnostics: dict[str, Any] | None) -> bool:
    """Return whether a successful internet-backed result contributed to routing."""
    diagnostics = source_diagnostics if isinstance(source_diagnostics, dict) else {}
    analytics = diagnostics.get("router_analytics")
    hits = analytics.get("hits") if isinstance(analytics, dict) else None
    if isinstance(hits, dict) and "internet" in hits:
        return _positive_hit_count(hits.get("internet"))

    internet = diagnostics.get("internet")
    return bool(
        isinstance(internet, dict)
        and internet.get("success") is True
        and diagnostics.get("source") in {"Internet", "Giphy", "Cache"}
    )


def internet_used_from_audit_details(details: dict[str, Any] | None) -> bool:
    """Read the explicit flag when present, with a safe legacy-row fallback."""
    audit_details = details if isinstance(details, dict) else {}
    if "internet_used" in audit_details:
        return bool(audit_details["internet_used"])

    diagnostics = audit_details.get("source_diagnostics")
    if isinstance(diagnostics, dict):
        return internet_used_from_diagnostics(diagnostics)

    analytics = audit_details.get("router_analytics")
    hits = analytics.get("hits") if isinstance(analytics, dict) else None
    return bool(isinstance(hits, dict) and _positive_hit_count(hits.get("internet")))


def finalize_router_decision_audit(
    existing_details: dict[str, Any] | None,
    source_diagnostics: dict[str, Any] | None,
) -> dict[str, Any]:
    """Refresh a flushed audit snapshot after routing and authority diagnostics settle."""
    details = dict(existing_details) if isinstance(existing_details, dict) else {}
    diagnostics = dict(source_diagnostics) if isinstance(source_diagnostics, dict) else {}
    analytics = diagnostics.get("router_analytics")

    details["source_diagnostics"] = diagnostics
    details["router_analytics"] = analytics if isinstance(analytics, dict) else {}
    details["internet_used"] = internet_used_from_diagnostics(diagnostics)
    return details
