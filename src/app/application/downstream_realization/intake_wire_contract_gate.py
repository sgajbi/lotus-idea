from __future__ import annotations

import json
from pathlib import Path


DOWNSTREAM_INTAKE_WIRE_CONTRACT_PATH = Path(
    "contracts/downstream-realization/lotus-idea-downstream-intake-wire-contract.v1.json"
)
_REQUIRED_INTAKE_REQUEST_FIELDS = {
    "source_system",
    "source_product",
    "idea_candidate_id",
    "conversion_intent_id",
    "intent_type",
    "source_refs",
}
# Both shipped conversion intakes (advise#608, manage#660) require the
# authoritative portfolio scope in the request body.
_REQUIRED_CONVERSION_INTAKE_REQUEST_FIELDS = _REQUIRED_INTAKE_REQUEST_FIELDS | {"portfolio_id"}
_REQUIRED_REPORT_INTAKE_PAYLOAD_FIELDS = {
    "report_evidence_pack_id",
    "conversion_intent_id",
    "candidate_id",
    "purpose",
    "evidence_packet_id",
    "evidence_content_fingerprint",
    "source_signal_ids",
    "source_summaries",
    "reason_codes",
    "report_source_authority",
    "render_source_authority",
    "archive_source_authority",
    "boundary",
    "retention_policy_ref",
    "requested_at_utc",
    "grants_client_publication_authority",
    "creates_rendered_output",
    "creates_archive_record",
    "producer",
    "supportability_status",
}
_REQUIRED_REPORT_MATERIALIZATION_REQUEST_FIELDS = {
    "idea_evidence_pack",
    "portfolio_id",
    "as_of_date",
    "requested_output_formats",
    "boundary",
    "grants_client_publication_authority",
    "producer",
    "supportability_status",
}
_REQUIRED_REPORT_MATERIALIZATION_RECEIPT_FIELDS = {
    "report_request_id",
    "report_job_id",
    "status",
    "materialization_status",
    "status_url",
    "idempotency_key",
    "report_package_identity",
    "producer",
    "source_authority",
    "materialization_proven",
    "creates_report_job",
    "creates_rendered_output",
    "creates_archive_record",
    "grants_client_publication_authority",
    "supported_feature_promoted",
    "supportability_status",
    "remaining_blockers",
    "evidence_refs",
    "render_job_id",
    "archive_document_id",
}
_INTAKE_RECEIPT_OUTCOMES = ["ACCEPTED", "ACCEPTED_REPLAYED", "REJECTED"]
_MANAGE_HISTORY_RESPONSE_FIELDS = {
    "contract_version",
    "source_authority",
    "intake_id",
    "management_action_id",
    "portfolio_id",
    "idea_candidate_id",
    "conversion_intent_id",
    "status",
    "source_event_version",
    "events",
    "rebalance_execution_proven",
    "order_execution_proven",
    "client_publication_proven",
}
_ADVISE_HISTORY_RESPONSE_FIELDS = {
    "realization_id",
    "intake_id",
    "review_work_id",
    "review_work_status",
    "source_authority",
    "realization_authority",
    "tenant_id",
    "legal_entity_code",
    "portfolio_id",
    "idea_candidate_id",
    "conversion_intent_id",
    "source_evidence_fingerprint",
    "current_status",
    "current_source_event_version",
    "proposal_id",
    "proposal_record_created",
    "suitability_authority_granted",
    "order_created",
    "client_publication_authorized",
    "created_at_utc",
    "updated_at_utc",
    "outcomes",
}
_TRUSTED_SERVICE_HEADERS = {
    "X-Actor-Id",
    "X-Role",
    "X-Tenant-Id",
    "X-Legal-Entity-Code",
    "X-Service-Identity",
    "X-Capabilities",
    "X-Principal-Status",
}
_EXPECTED_INTAKE_CONSUMERS: dict[str, dict[str, object]] = {
    "advise_proposal": {
        "owner_repository": "lotus-advise",
        "owner_route": "POST /advisory/proposals/idea-intake",
        "intent_type": "REVIEW_FOR_ADVISORY_PROPOSAL",
        "receipt_outcomes": _INTAKE_RECEIPT_OUTCOMES,
        "principal_capability": "advisory.idea_proposal_intake.accept",
        "owner_history_route": ("GET /advisory/proposals/idea-intake/{intake_id}/realization"),
        "owner_recovery_history_route": (
            "GET /advisory/proposals/idea-intake/by-conversion-intent/"
            "{conversion_intent_id}/realization"
        ),
        "history_principal_capability": "advisory.idea_proposal_realization.read",
        "history_response_fields": _ADVISE_HISTORY_RESPONSE_FIELDS,
        "history_required_server_headers": _TRUSTED_SERVICE_HEADERS
        | {"X-Portfolio-Id", "X-Authorized-Portfolio-Id"},
        "local_dev_principal_source": "trusted_headers_until_production_idp_available",
        "required_server_headers": _TRUSTED_SERVICE_HEADERS,
        "request_fields": _REQUIRED_CONVERSION_INTAKE_REQUEST_FIELDS,
        "scope_boundary": {
            "portfolio_source": "governed_candidate_access_scope",
            "complete_caller_entitlement_required": True,
            "idempotency_scope_fields": [
                "tenant_id",
                "book_id",
                "portfolio_id",
                "client_id",
            ],
            "client_id_exposed": False,
        },
    },
    "manage_review": {
        "owner_repository": "lotus-manage",
        "owner_route": "POST /api/v1/rebalance/idea-action-intake",
        "intent_type": "REVIEW_FOR_REBALANCE",
        "receipt_outcomes": _INTAKE_RECEIPT_OUTCOMES,
        "principal_capability": "manage.idea_action_intake.accept",
        "owner_history_route": ("GET /api/v1/rebalance/idea-action-intakes/{intake_id}/outcomes"),
        "history_principal_capability": "manage.idea_action_intake.read",
        "history_response_fields": _MANAGE_HISTORY_RESPONSE_FIELDS,
        "history_required_server_headers": _TRUSTED_SERVICE_HEADERS | {"X-Portfolio-Ids"},
        "local_dev_principal_source": "trusted_headers_until_production_idp_available",
        "required_server_headers": _TRUSTED_SERVICE_HEADERS | {"X-Portfolio-Ids"},
        "request_fields": _REQUIRED_CONVERSION_INTAKE_REQUEST_FIELDS,
        "scope_boundary": {
            "portfolio_source": "governed_candidate_access_scope",
            "complete_caller_entitlement_required": True,
            "idempotency_scope_fields": [
                "tenant_id",
                "book_id",
                "portfolio_id",
                "client_id",
            ],
            "client_id_exposed": False,
        },
    },
    "report_evidence": {
        "owner_repository": "lotus-report",
        "owner_route": "POST /reports/idea-evidence-packs/materializations",
        "request_fields": _REQUIRED_REPORT_MATERIALIZATION_REQUEST_FIELDS,
        "idea_evidence_pack_fields": _REQUIRED_REPORT_INTAKE_PAYLOAD_FIELDS,
        "purpose_mapping": {
            "client_review_report_section": "CLIENT_REPORT_EVIDENCE",
            "advisor_review_evidence": "ADVISOR_REVIEW_APPENDIX",
            "audit_evidence": "ADVISOR_REVIEW_APPENDIX",
        },
        "owner_retention_policy_mapping": {
            "lotus-report:idea-evidence-retention:v1": "generated-report-standard",
        },
        "local_test_service_context": {
            "tenant_id": "tenant-sg",
            "region": "APAC",
            "output_formats": ["json"],
        },
        "boundary": "REPORT_JOB_MATERIALIZATION",
        "required_server_headers": {
            "X-Actor-Id",
            "X-Caller-Application",
            "X-Tenant-Id",
            "X-Region",
        },
        "receipt_response_fields": _REQUIRED_REPORT_MATERIALIZATION_RECEIPT_FIELDS,
        "receipt_invariants": {
            "exact_submission_identity_required": True,
            "exact_idempotency_key_required": True,
            "client_publication_authority_forbidden": True,
            "supported_feature_promotion_forbidden": True,
            "malformed_receipt_requires_reconciliation": True,
            "persist_exact_owner_receipt": True,
        },
        "receipt_source_authority": {
            "idea_evidence": "lotus-idea",
            "report_materialization": "lotus-report",
            "rendering": "lotus-render",
            "archive_record": "lotus-archive",
            "client_publication": "blocked",
        },
        "receipt_required_blockers": [
            "client_publication_authority_blocked",
            "supported_feature_promotion_missing",
        ],
    },
}
_INTAKE_SECURITY_BOUNDARY_REQUIRED_TRUE_FIELDS = (
    "development_fixture_only",
    "browser_supplied_identity_headers_forbidden",
    "idp_session_and_token_claim_mapping_deferred",
    "does_not_grant_downstream_business_authority",
)
_REPORT_INTAKE_CONSUMER_FIELDS = (
    "purpose_mapping",
    "owner_retention_policy_mapping",
    "local_test_service_context",
    "boundary",
    "idea_evidence_pack_fields",
    "receipt_response_fields",
    "receipt_invariants",
    "receipt_source_authority",
    "receipt_required_blockers",
)


def validate_downstream_intake_wire_contract(repository_root: Path) -> list[str]:
    path = repository_root / DOWNSTREAM_INTAKE_WIRE_CONTRACT_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"downstream intake wire contract is unreadable: {exc}"]
    if not isinstance(payload, dict):
        return ["downstream intake wire contract must be a JSON object"]

    errors: list[str] = []
    errors.extend(_validate_downstream_intake_contract_envelope(payload))
    errors.extend(_validate_downstream_intake_security_boundary(payload))

    consumers = payload.get("consumer_contracts")
    if not isinstance(consumers, list) or not all(isinstance(item, dict) for item in consumers):
        return errors + ["downstream intake wire contract consumer_contracts must be objects"]

    by_target = _downstream_intake_consumers_by_target(consumers)
    errors.extend(_validate_downstream_intake_consumer_inventory(by_target))
    errors.extend(_validate_downstream_intake_consumer_contracts(by_target))
    return errors


def _validate_downstream_intake_contract_envelope(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if payload.get("contract_id") != "lotus-idea-downstream-intake-wire-contract":
        errors.append("downstream intake wire contract has an unexpected contract_id")
    if payload.get("contract_version") != "1.10.0":
        errors.append("downstream intake wire contract must be version 1.10.0")
    if payload.get("repository") != "lotus-idea":
        errors.append("downstream intake wire contract repository must be lotus-idea")
    if payload.get("lifecycle_status") != "development_only":
        errors.append("downstream intake wire contract must remain development_only")
    if payload.get("supportability_status") != "not_certified":
        errors.append("downstream intake wire contract must remain not_certified")
    if payload.get("non_authoritative") is not True:
        errors.append("downstream intake wire contract must remain non_authoritative")
    return errors


def _validate_downstream_intake_security_boundary(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    security_boundary = payload.get("security_boundary")
    if not isinstance(security_boundary, dict):
        errors.append("downstream intake wire contract security_boundary must be an object")
    else:
        for field in _INTAKE_SECURITY_BOUNDARY_REQUIRED_TRUE_FIELDS:
            if security_boundary.get(field) is not True:
                errors.append(
                    f"downstream intake wire contract security_boundary.{field} must be true"
                )
    return errors


def _downstream_intake_consumers_by_target(
    consumers: list[object],
) -> dict[str, dict[str, object]]:
    typed_consumers = [item for item in consumers if isinstance(item, dict)]
    return {str(item.get("conversion_target", "")): item for item in typed_consumers}


def _validate_downstream_intake_consumer_inventory(
    by_target: dict[str, dict[str, object]],
) -> list[str]:
    if set(by_target) != set(_EXPECTED_INTAKE_CONSUMERS):
        return [
            "downstream intake wire contract must declare exactly Advise, Manage, and Report consumers"
        ]
    return []


def _validate_downstream_intake_consumer_contracts(
    by_target: dict[str, dict[str, object]],
) -> list[str]:
    errors: list[str] = []
    for target, expected in _EXPECTED_INTAKE_CONSUMERS.items():
        consumer = by_target.get(target)
        if consumer is None:
            continue
        errors.extend(_validate_downstream_intake_owner_fields(target, consumer, expected))
        if target == "report_evidence":
            errors.extend(_validate_report_evidence_intake_consumer(target, consumer, expected))
        else:
            errors.extend(_validate_advise_manage_intake_consumer(target, consumer, expected))
        errors.extend(_validate_downstream_intake_request_fields(target, consumer, expected))
        errors.extend(_validate_downstream_intake_server_headers(target, consumer, expected))
    return errors


def _validate_downstream_intake_owner_fields(
    target: str,
    consumer: dict[str, object],
    expected: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    for field in ("owner_repository", "owner_route"):
        if consumer.get(field) != expected[field]:
            errors.append(f"{target} intake wire contract {field} drifted")
    return errors


def _validate_advise_manage_intake_consumer(
    target: str,
    consumer: dict[str, object],
    expected: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    if consumer.get("intent_type") != expected["intent_type"]:
        errors.append(f"{target} intake wire contract intent_type drifted")
    for field in (
        "receipt_outcomes",
        "principal_capability",
        "local_dev_principal_source",
    ):
        if consumer.get(field) != expected[field]:
            errors.append(f"{target} intake wire contract {field} drifted")
    if (
        "scope_boundary" in expected
        and consumer.get("scope_boundary") != expected["scope_boundary"]
    ):
        errors.append(f"{target} intake wire contract scope_boundary drifted")
    if "owner_history_route" in expected:
        for field in ("owner_history_route", "history_principal_capability"):
            if consumer.get(field) != expected[field]:
                errors.append(f"{target} intake wire contract {field} drifted")
        for field in ("history_response_fields", "history_required_server_headers"):
            actual = consumer.get(field)
            if not isinstance(actual, list) or set(actual) != expected[field]:
                errors.append(f"{target} intake wire contract {field} drifted")
    return errors


def _validate_report_evidence_intake_consumer(
    target: str,
    consumer: dict[str, object],
    expected: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    for field in _REPORT_INTAKE_CONSUMER_FIELDS:
        actual = consumer.get(field)
        expected_value = expected[field]
        if field in {"idea_evidence_pack_fields", "receipt_response_fields"}:
            matches = isinstance(actual, list) and set(actual) == expected_value
        else:
            matches = actual == expected_value
        if not matches:
            errors.append(f"{target} intake wire contract {field} drifted")
    return errors


def _validate_downstream_intake_request_fields(
    target: str,
    consumer: dict[str, object],
    expected: dict[str, object],
) -> list[str]:
    expected_fields = expected.get("request_fields", _REQUIRED_INTAKE_REQUEST_FIELDS)
    request_fields = consumer.get("request_fields")
    if not isinstance(request_fields, list) or set(request_fields) != expected_fields:
        return [f"{target} intake wire contract request_fields drifted"]
    return []


def _validate_downstream_intake_server_headers(
    target: str,
    consumer: dict[str, object],
    expected: dict[str, object],
) -> list[str]:
    headers = consumer.get("required_server_headers")
    if not isinstance(headers, list) or set(headers) != expected["required_server_headers"]:
        return [f"{target} intake wire contract required_server_headers drifted"]
    return []
