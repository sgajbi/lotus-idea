# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.downstream_realization_contracts import (  # noqa: E402
    DOWNSTREAM_CONTRACT_PLAN_PATH,
    DownstreamRealizationContractPlan,
    downstream_realization_contract_plan_from_payload,
    load_downstream_realization_contract_plan,
)
from app.application.downstream_realization_issue_refs import (  # noqa: E402
    validate_downstream_blocker_issue_refs,
)


REQUIRED_CONTRACTS = {
    "lotus-idea-to-lotus-advise-proposal-intake:v1": "lotus-advise",
    "lotus-idea-to-lotus-manage-action-intake:v1": "lotus-manage",
    "lotus-idea-to-lotus-report-evidence-pack-intake:v1": "lotus-report",
}
REQUIRED_EVIDENCE_REFS = {
    "lotus-idea-to-lotus-advise-proposal-intake:v1": {
        "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
        "POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions",
        "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
    },
    "lotus-idea-to-lotus-manage-action-intake:v1": {
        "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
        "POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions",
        "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
    },
    "lotus-idea-to-lotus-report-evidence-pack-intake:v1": {
        "POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
        "POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions",
        "lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json",
        "lotus-render",
        "lotus-archive",
    },
}
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
_INTAKE_RECEIPT_OUTCOMES = ["ACCEPTED", "ACCEPTED_REPLAYED", "REJECTED"]
_TRUSTED_SERVICE_HEADERS = {
    "X-Actor-Id",
    "X-Role",
    "X-Tenant-Id",
    "X-Legal-Entity-Code",
    "X-Service-Identity",
    "X-Capabilities",
    "X-Principal-Status",
}
_EXPECTED_INTAKE_CONSUMERS = {
    "advise_proposal": {
        "owner_repository": "lotus-advise",
        "owner_route": "POST /advisory/proposals/idea-intake",
        "intent_type": "REVIEW_FOR_ADVISORY_PROPOSAL",
        "receipt_outcomes": _INTAKE_RECEIPT_OUTCOMES,
        "principal_capability": "advisory.idea_proposal_intake.accept",
        "local_dev_principal_source": "trusted_headers_until_production_idp_available",
        "required_server_headers": _TRUSTED_SERVICE_HEADERS,
    },
    "manage_review": {
        "owner_repository": "lotus-manage",
        "owner_route": "POST /api/v1/rebalance/idea-action-intake",
        "intent_type": "REVIEW_FOR_REBALANCE",
        "receipt_outcomes": _INTAKE_RECEIPT_OUTCOMES,
        "principal_capability": "manage.idea_action_intake.accept",
        "local_dev_principal_source": "trusted_headers_until_production_idp_available",
        "required_server_headers": _TRUSTED_SERVICE_HEADERS,
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
    },
}


def validate_downstream_realization_contract_plan(
    *,
    repository_root: Path = ROOT,
    contract_path: Path = DOWNSTREAM_CONTRACT_PLAN_PATH,
) -> list[str]:
    plan = load_downstream_realization_contract_plan(
        repository_root=repository_root,
        contract_path=contract_path,
    )
    return validate_downstream_realization_contract_plan_payload(
        plan,
        repository_root=repository_root,
    )


def validate_downstream_realization_contract_plan_payload(
    plan: DownstreamRealizationContractPlan,
    *,
    repository_root: Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    if plan.contract_id != "lotus-idea-downstream-realization-contract-plan":
        errors.append(
            "downstream contract plan contract_id must be "
            "`lotus-idea-downstream-realization-contract-plan`"
        )
    if plan.contract_version != "1.0.0":
        errors.append("downstream contract plan contract_version must be 1.0.0")
    if plan.repository != "lotus-idea":
        errors.append("downstream contract plan repository must be lotus-idea")
    if plan.lifecycle_status != "planned":
        errors.append("downstream contract plan lifecycle_status must remain planned")
    if plan.supportability_status != "not_certified":
        errors.append("downstream contract plan supportability_status must remain not_certified")
    if plan.route_existence_proven:
        errors.append("downstream contract plan must not claim route existence proof")
    if plan.downstream_execution_proven:
        errors.append("downstream contract plan must not claim downstream execution proof")
    if plan.supported_feature_promoted:
        errors.append("downstream contract plan must not promote supported features")

    errors.extend(_validate_source_of_truth(plan, repository_root=repository_root))
    errors.extend(_validate_downstream_intake_wire_contract(repository_root))
    errors.extend(_validate_contracts(plan))
    errors.extend(_validate_durable_submission_state_machine(repository_root))
    return errors


def _validate_source_of_truth(
    plan: DownstreamRealizationContractPlan,
    *,
    repository_root: Path,
) -> list[str]:
    errors: list[str] = []
    required_keys = {
        "readiness_builder",
        "contract_loader",
        "downstream_realization_orchestration",
        "downstream_realization_api",
        "downstream_adapter_port",
        "downstream_adapter_foundation",
        "downstream_intake_wire_contract",
        "downstream_submission_state",
        "downstream_submission_postgres",
        "downstream_submission_migration",
        "downstream_reconciliation_application",
        "downstream_reconciliation_api",
        "downstream_submission_postgres_proof",
        "contract_gate",
        "operations_runbook",
        "rfc_slice_12",
        "rfc_slice_13",
    }
    missing_keys = sorted(required_keys - set(plan.source_of_truth))
    if missing_keys:
        errors.append(
            "downstream contract plan source_of_truth missing keys: " + ", ".join(missing_keys)
        )
    for key, relative_path in sorted(plan.source_of_truth.items()):
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"downstream contract plan source_of_truth.{key} path must stay relative")
            continue
        if not (repository_root / path).exists():
            errors.append(f"downstream contract plan source_of_truth.{key} path missing")
    return errors


def _validate_downstream_intake_wire_contract(repository_root: Path) -> list[str]:
    path = repository_root / DOWNSTREAM_INTAKE_WIRE_CONTRACT_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"downstream intake wire contract is unreadable: {exc}"]
    if not isinstance(payload, dict):
        return ["downstream intake wire contract must be a JSON object"]

    errors: list[str] = []
    if payload.get("contract_id") != "lotus-idea-downstream-intake-wire-contract":
        errors.append("downstream intake wire contract has an unexpected contract_id")
    if payload.get("contract_version") != "1.5.0":
        errors.append("downstream intake wire contract must be version 1.5.0")
    if payload.get("repository") != "lotus-idea":
        errors.append("downstream intake wire contract repository must be lotus-idea")
    if payload.get("lifecycle_status") != "development_only":
        errors.append("downstream intake wire contract must remain development_only")
    if payload.get("supportability_status") != "not_certified":
        errors.append("downstream intake wire contract must remain not_certified")
    if payload.get("non_authoritative") is not True:
        errors.append("downstream intake wire contract must remain non_authoritative")

    security_boundary = payload.get("security_boundary")
    if not isinstance(security_boundary, dict):
        errors.append("downstream intake wire contract security_boundary must be an object")
    else:
        for field in (
            "development_fixture_only",
            "browser_supplied_identity_headers_forbidden",
            "idp_session_and_token_claim_mapping_deferred",
            "does_not_grant_downstream_business_authority",
        ):
            if security_boundary.get(field) is not True:
                errors.append(
                    f"downstream intake wire contract security_boundary.{field} must be true"
                )

    consumers = payload.get("consumer_contracts")
    if not isinstance(consumers, list) or not all(isinstance(item, dict) for item in consumers):
        return errors + ["downstream intake wire contract consumer_contracts must be objects"]
    by_target = {str(item.get("conversion_target", "")): item for item in consumers}
    if set(by_target) != set(_EXPECTED_INTAKE_CONSUMERS):
        errors.append(
            "downstream intake wire contract must declare exactly Advise, Manage, and Report consumers"
        )
    for target, expected in _EXPECTED_INTAKE_CONSUMERS.items():
        consumer = by_target.get(target)
        if consumer is None:
            continue
        for field in ("owner_repository", "owner_route"):
            if consumer.get(field) != expected[field]:
                errors.append(f"{target} intake wire contract {field} drifted")
        if target != "report_evidence" and consumer.get("intent_type") != expected["intent_type"]:
            errors.append(f"{target} intake wire contract intent_type drifted")
        if target != "report_evidence":
            for field in (
                "receipt_outcomes",
                "principal_capability",
                "local_dev_principal_source",
            ):
                if consumer.get(field) != expected[field]:
                    errors.append(f"{target} intake wire contract {field} drifted")
        request_fields = consumer.get("request_fields")
        if not isinstance(request_fields, list) or set(request_fields) != expected.get(
            "request_fields", _REQUIRED_INTAKE_REQUEST_FIELDS
        ):
            errors.append(f"{target} intake wire contract request_fields drifted")
        if target == "report_evidence":
            for field in (
                "purpose_mapping",
                "owner_retention_policy_mapping",
                "local_test_service_context",
                "boundary",
                "idea_evidence_pack_fields",
            ):
                actual = consumer.get(field)
                expected_value = expected[field]
                if field == "idea_evidence_pack_fields":
                    matches = isinstance(actual, list) and set(actual) == expected_value
                else:
                    matches = actual == expected_value
                if not matches:
                    errors.append(f"{target} intake wire contract {field} drifted")
        headers = consumer.get("required_server_headers")
        if not isinstance(headers, list) or set(headers) != expected["required_server_headers"]:
            errors.append(f"{target} intake wire contract required_server_headers drifted")
    return errors


def _validate_durable_submission_state_machine(repository_root: Path) -> list[str]:
    orchestration = _read(
        repository_root, "src/app/application/downstream_realization/submission_use_cases.py"
    )
    postgres = _read(
        repository_root,
        "src/app/infrastructure/postgres_downstream_submission.py",
    )
    migration = _read(
        repository_root,
        "migrations/008_downstream_submission_state_machine.sql",
    )
    reconciliation_api = _read(
        repository_root,
        "src/app/api/downstream_submission_reconciliation.py",
    )
    makefile = _read(repository_root, "Makefile")
    errors: list[str] = []
    required_fragments = {
        "downstream orchestration": (
            orchestration,
            (
                "claim_downstream_submission",
                "finalize_downstream_submission",
                "DownstreamRealizationStatus.RECONCILIATION_REQUIRED",
                "downstream_submission_finalization_failed",
            ),
        ),
        "PostgreSQL submission adapter": (
            postgres,
            (
                "ON CONFLICT DO NOTHING",
                "FOR UPDATE",
                "downstream submission support reference collision",
                "downstream-submission-state-update",
            ),
        ),
        "submission migration": (
            migration,
            (
                "support_reference",
                "lease_attempt_id",
                "audit_json JSONB",
                "idx_idea_downstream_submission_reconciliation",
            ),
        ),
        "reconciliation API": (
            reconciliation_api,
            (
                "idea.downstream-reconciliation.read",
                "idea.downstream-reconciliation.resolve",
                "require_role_and_capability",
                "Idempotency-Key must be valid and equal changeReference",
            ),
        ),
        "PostgreSQL integration gate": (
            makefile,
            ("tests/integration/test_postgres_downstream_submission_runtime.py",),
        ),
    }
    for label, (source, fragments) in required_fragments.items():
        for fragment in fragments:
            if fragment not in source:
                errors.append(f"{label} missing durable submission fragment: {fragment}")
    claim_position = orchestration.find("claim_downstream_submission")
    call_position = orchestration.find("outcome = call()")
    if claim_position < 0 or call_position < 0 or claim_position > call_position:
        errors.append("downstream orchestration must durably claim before the external call")
    source_tree = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((repository_root / "src").rglob("*.py"))
    )
    if "record_downstream_submission(" in source_tree:
        errors.append("legacy post-call downstream submission writes must remain removed")
    return errors


def _read(repository_root: Path, relative_path: str) -> str:
    path = repository_root / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _validate_contracts(plan: DownstreamRealizationContractPlan) -> list[str]:
    errors: list[str] = []
    declared_contracts = {contract.contract_id: contract for contract in plan.contracts}
    missing_contracts = sorted(set(REQUIRED_CONTRACTS) - set(declared_contracts))
    extra_contracts = sorted(set(declared_contracts) - set(REQUIRED_CONTRACTS))
    if missing_contracts:
        errors.append("downstream contract plan missing contracts: " + ", ".join(missing_contracts))
    if extra_contracts:
        errors.append(
            "downstream contract plan contains unsupported contracts: " + ", ".join(extra_contracts)
        )

    for contract_id, owner_repository in sorted(REQUIRED_CONTRACTS.items()):
        contract = declared_contracts.get(contract_id)
        if contract is None:
            continue
        if contract.owner_repository != owner_repository:
            errors.append(f"{contract_id}: owner_repository must be {owner_repository}")
        if contract.source_authority != owner_repository:
            errors.append(f"{contract_id}: source_authority must be {owner_repository}")
        if not contract.target_route.startswith("planned:"):
            errors.append(f"{contract_id}: target_route must remain planned before route proof")
        if contract.route_fit_status != "not_certified":
            errors.append(f"{contract_id}: route_fit_status must remain not_certified")
        if contract.adapter_status != "adapter_foundation_present":
            errors.append(f"{contract_id}: adapter_status must be adapter_foundation_present")
        if not contract.blockers:
            errors.append(f"{contract_id}: blockers are required before certification")
        errors.extend(
            validate_downstream_blocker_issue_refs(
                contract_id=contract_id,
                blockers=contract.blockers,
                blocker_issue_refs=contract.blocker_issue_refs,
            )
        )

        missing_refs = sorted(REQUIRED_EVIDENCE_REFS[contract_id] - set(contract.evidence_refs))
        if missing_refs:
            errors.append(
                f"{contract_id}: evidence_refs missing required references: "
                + ", ".join(missing_refs)
            )
        if _has_sensitive_or_executable_route_claim(contract.evidence_refs):
            errors.append(
                f"{contract_id}: evidence_refs must not include downstream current routes"
            )
    return errors


def _has_sensitive_or_executable_route_claim(evidence_refs: tuple[str, ...]) -> bool:
    return any(
        ref.startswith(("GET http", "POST http", "PUT http", "PATCH http", "DELETE http"))
        for ref in evidence_refs
    )


_parse_payload = downstream_realization_contract_plan_from_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate lotus-idea downstream realization contract posture."
    )
    parser.add_argument(
        "--contract-path",
        type=Path,
        default=DOWNSTREAM_CONTRACT_PLAN_PATH,
        help="Repository-relative downstream realization contract plan path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_downstream_realization_contract_plan(contract_path=args.contract_path)
    if errors:
        print("\n".join(errors))
        return 1
    print("Downstream realization contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
