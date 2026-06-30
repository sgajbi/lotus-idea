from __future__ import annotations

import json
from pathlib import Path

from scripts.supported_features_gate import validate_supported_features


def _base_registry() -> dict[str, object]:
    return {
        "repository": "lotus-idea",
        "schema": "supported-features/supported-features.schema.json",
        "policy": "Only implementation-backed behavior may be promoted to supported.",
        "current_posture": "foundation_only",
        "features": [],
        "planned_capabilities": [
            {
                "id": "idea-lifecycle",
                "name": "Idea lifecycle and review state",
                "governing_rfc": (
                    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
                    "RFC-0002-enterprise-opportunity-intelligence-operating-layer.md"
                ),
                "status": "planned",
            }
        ],
    }


def _valid_implemented_feature() -> dict[str, object]:
    return {
        "id": "advisor-review-queue",
        "name": "Advisor review queue",
        "owner": "lotus-idea",
        "status": "implemented",
        "governing_rfc": (
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
            "RFC-0002-slice-07-scoring-ranking-suppression-and-queue-policy.md"
        ),
        "support_scope": (
            "Bounded advisor queue projection over persisted idea candidates for internal "
            "advisor review."
        ),
        "unsupported_scope": (
            "No client-ready publication, full Workbench certification, data-product "
            "certification, or autonomous recommendation support."
        ),
        "api_surfaces": [
            {
                "method": "GET",
                "path": "/api/v1/review-queues/advisor",
                "endpoint_certification_ref": "docs/operations/endpoint-certification-ledger.json",
            }
        ],
        "ui_surfaces": [
            {
                "surface": "lotus-workbench advisor queue",
                "state": "bounded read-only rendering evidence only",
                "evidence_ref": "wiki/Supported-Features.md",
            }
        ],
        "source_dependencies": [
            {
                "repository": "lotus-core",
                "product_or_contract": "PortfolioStateSnapshot:v1",
                "authority_boundary": (
                    "lotus-core remains authoritative for portfolio, holding, client, and "
                    "mandate facts."
                ),
            }
        ],
        "consumer_publication_state": "bounded internal API; external support not promoted",
        "gateway_workbench_state": "bounded read-only publication evidence; full proof pending",
        "data_product_state": "not_certified",
        "promotion_evidence": {
            "code_modules": [
                "src/app/application/review_queue.py",
                "src/app/api/review_queues.py",
            ],
            "api_contracts": [
                "docs/operations/endpoint-certification-ledger.json",
                "docs/operations/api-certification.md",
            ],
            "test_evidence": [
                (
                    "tests/integration/test_review_queue_api.py::"
                    "test_advisor_review_queue_api_projects_persisted_candidates"
                ),
                (
                    "tests/integration/test_review_queue_api.py::"
                    "test_advisor_review_queue_api_requires_read_permission"
                ),
            ],
            "runtime_evidence": [
                "docs/operations/implementation-proof-readiness.md",
            ],
            "ci_evidence": {
                "local_gates": [
                    "make supported-features-gate",
                    "make endpoint-certification-gate",
                    "make check",
                ],
                "github_checks": [
                    "Feature Lane",
                    "PR Merge Gate",
                ],
            },
            "documentation": [
                "README.md",
                "wiki/Supported-Features.md",
            ],
            "runbooks": [
                "docs/operations/api-certification.md",
            ],
            "proof_artifacts": [
                "docs/operations/implementation-proof-readiness.md",
            ],
        },
        "known_gaps": [
            "Full Workbench live proof and client-publication evidence remain out of scope.",
        ],
        "last_reviewed_utc": "2026-06-30T00:00:00Z",
        "promotion_decision_ref": "PR evidence and issue #241 acceptance criteria",
    }


def test_supported_features_gate_accepts_current_empty_registry() -> None:
    payload = json.loads(Path("supported-features/supported-features.json").read_text())

    assert validate_supported_features(payload) == []


def test_supported_features_gate_rejects_string_only_promotion_evidence() -> None:
    payload = _base_registry()
    payload["features"] = [
        {
            "id": "advisor-review-queue",
            "name": "Advisor review queue",
            "status": "implemented",
            "promotion_evidence": "placeholder",
        }
    ]

    errors = validate_supported_features(payload)

    assert any("implemented feature missing fields" in error for error in errors)


def test_supported_features_gate_rejects_implemented_entry_without_proof_artifacts() -> None:
    payload = _base_registry()
    feature = _valid_implemented_feature()
    promotion_evidence = feature["promotion_evidence"]
    assert isinstance(promotion_evidence, dict)
    promotion_evidence = dict(promotion_evidence)
    promotion_evidence.pop("proof_artifacts")
    feature["promotion_evidence"] = promotion_evidence
    payload["features"] = [feature]

    errors = validate_supported_features(payload)

    assert any("promotion_evidence missing fields: proof_artifacts" in error for error in errors)


def test_supported_features_gate_rejects_unknown_endpoint_promotion() -> None:
    payload = _base_registry()
    feature = _valid_implemented_feature()
    feature["api_surfaces"] = [
        {
            "method": "GET",
            "path": "/api/v1/not-a-certified-route",
            "endpoint_certification_ref": "docs/operations/endpoint-certification-ledger.json",
        }
    ]
    payload["features"] = [feature]

    errors = validate_supported_features(payload)

    assert any("endpoint certification ledger operation" in error for error in errors)


def test_supported_features_gate_accepts_structured_implemented_entry() -> None:
    payload = _base_registry()
    payload["features"] = [_valid_implemented_feature()]

    assert validate_supported_features(payload) == []
