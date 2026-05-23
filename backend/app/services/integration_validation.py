"""Type-aware integration documentation completeness validation.

Implements the per-type rule sets from the Phase 3 brief. Each rule checks the
integration's metadata and attached contract; failures become validation items.
"""
from __future__ import annotations

import json

from app.models import Integration
from app.schemas import ValidationItem


def _metadata(integration: Integration) -> dict:
    try:
        data = json.loads(integration.metadata_json or "{}")
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _has(metadata: dict, key: str) -> bool:
    value = metadata.get(key)
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def _has_contract(integration: Integration) -> bool:
    return bool((integration.contract_content or "").strip())


# Per type: list of (label, predicate, severity). Predicate gets (integration, metadata).
_RULES: dict[str, list[tuple]] = {
    "GRPC": [
        ("Proto contract is attached", lambda i, m: _has_contract(i), "error"),
        ("Proto package is defined", lambda i, m: _has(m, "proto_package"), "error"),
        ("gRPC service name is documented",
         lambda i, m: _has(m, "grpc_service"), "error"),
        ("RPC methods are listed", lambda i, m: _has(m, "methods"), "error"),
        ("Streaming type is defined",
         lambda i, m: _has(m, "streaming_type"), "warning"),
        ("Deadline / timeout is defined",
         lambda i, m: _has(m, "deadline_ms"), "warning"),
        ("Retry policy is defined", lambda i, m: _has(m, "retry_policy"), "warning"),
        ("Idempotency behavior is defined",
         lambda i, m: "idempotency_required" in m, "warning"),
        ("Authentication is documented",
         lambda i, m: _has(m, "authentication"), "warning"),
    ],
    "KAFKA": [
        ("Topic is defined", lambda i, m: _has(m, "topic"), "error"),
        ("Producer is defined", lambda i, m: _has(m, "producer"), "error"),
        ("Consumer is defined", lambda i, m: _has(m, "consumer"), "error"),
        ("Schema format is defined",
         lambda i, m: _has(m, "schema_format") or _has_contract(i), "warning"),
        ("Retention is defined", lambda i, m: _has(m, "retention"), "warning"),
        ("Replay support is documented",
         lambda i, m: "replay_supported" in m, "warning"),
        ("DLQ behavior is documented",
         lambda i, m: _has(m, "dlq_behavior"), "warning"),
    ],
    "MQ": [
        ("Queue is defined", lambda i, m: _has(m, "queue_name"), "error"),
        ("Delivery guarantee is documented",
         lambda i, m: _has(m, "delivery_guarantee"), "error"),
        ("DLQ behavior is documented",
         lambda i, m: _has(m, "dead_letter_queue"), "warning"),
        ("Correlation ID is documented",
         lambda i, m: _has(m, "correlation_id"), "warning"),
    ],
    "SOAP": [
        ("WSDL is attached", lambda i, m: _has_contract(i), "error"),
        ("SOAP action is documented",
         lambda i, m: _has(m, "soap_action"), "error"),
        ("Fault handling is documented",
         lambda i, m: _has(m, "fault_handling"), "warning"),
        ("Legacy constraints are documented",
         lambda i, m: _has(m, "legacy_constraints"), "warning"),
    ],
    "REST": [
        ("OpenAPI contract is attached", lambda i, m: _has_contract(i), "warning"),
        ("Endpoints / methods are documented",
         lambda i, m: _has(m, "methods"), "warning"),
        ("Authentication is documented",
         lambda i, m: _has(m, "authentication"), "warning"),
    ],
    "FILE": [
        ("File format is documented",
         lambda i, m: _has(m, "file_format"), "warning"),
        ("Transfer protocol is documented",
         lambda i, m: _has(m, "transfer_protocol"), "warning"),
        ("Schedule is documented", lambda i, m: _has(m, "schedule"), "warning"),
    ],
    "BATCH": [
        ("Schedule is documented", lambda i, m: _has(m, "schedule"), "warning"),
        ("Dependencies are documented",
         lambda i, m: _has(m, "dependencies"), "warning"),
        ("SLA is documented", lambda i, m: _has(m, "sla"), "warning"),
    ],
}


def validate_integration(integration: Integration) -> list[ValidationItem]:
    """Run the type-aware completeness rules for one integration."""
    if integration.document_id is None:
        return [
            ValidationItem(
                severity="info",
                message="Integration has no document yet — create it first",
            )
        ]
    metadata = _metadata(integration)
    items: list[ValidationItem] = []
    for label, predicate, severity in _RULES.get(integration.type, []):
        try:
            ok = predicate(integration, metadata)
        except Exception:  # noqa: BLE001 — a broken rule must not break validation
            ok = False
        if not ok:
            items.append(
                ValidationItem(severity=severity, message=f"{label} — missing")
            )
    return items
