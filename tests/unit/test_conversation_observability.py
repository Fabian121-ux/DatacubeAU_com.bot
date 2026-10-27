from app.services.conversation_observability import (
    finalize_router_decision_audit,
    internet_used_from_audit_details,
    internet_used_from_diagnostics,
)


def test_final_audit_snapshot_preserves_context_and_captures_late_diagnostics():
    existing = {
        "question": "What did we decide?",
        "source_diagnostics": {"source": "FAQ"},
    }
    final_diagnostics = {
        "source": "FAQ",
        "outbound_authority": {"approval_required": True, "approval_id": 42},
        "memory": {"summaries_created": 1},
        "router_analytics": {"hits": {"internet": 0}, "selected_source": "FAQ"},
    }

    result = finalize_router_decision_audit(existing, final_diagnostics)

    assert result["question"] == "What did we decide?"
    assert result["source_diagnostics"] == final_diagnostics
    assert result["source_diagnostics"]["outbound_authority"]["approval_id"] == 42
    assert result["source_diagnostics"]["memory"]["summaries_created"] == 1
    assert result["router_analytics"] == final_diagnostics["router_analytics"]
    assert result["internet_used"] is False
    assert existing["source_diagnostics"] == {"source": "FAQ"}


def test_internet_used_is_true_for_successful_internet_result():
    diagnostics = {
        "source": "Internet",
        "internet": {"success": True},
        "router_analytics": {"hits": {"internet": 1}},
    }

    assert internet_used_from_diagnostics(diagnostics) is True
    assert finalize_router_decision_audit({}, diagnostics)["internet_used"] is True


def test_failed_internet_attempt_followed_by_fallback_is_not_counted_as_used():
    diagnostics = {
        "source": "AI",
        "internet": {"success": False, "error": "provider unavailable"},
        "router_analytics": {"hits": {"internet": 0}},
    }

    assert internet_used_from_diagnostics(diagnostics) is False
    assert internet_used_from_audit_details({"source_diagnostics": diagnostics}) is False


def test_legacy_audit_rows_can_derive_internet_used_from_diagnostics():
    legacy = {
        "source_diagnostics": {
            "source": "Cache",
            "internet": {"success": True},
        }
    }

    assert internet_used_from_audit_details(legacy) is True
    assert internet_used_from_audit_details({"internet_used": False, **legacy}) is False
