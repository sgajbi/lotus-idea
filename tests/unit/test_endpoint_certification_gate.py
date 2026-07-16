from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_endpoint_certification_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_certification_gate.py"
    spec = importlib.util.spec_from_file_location("endpoint_certification_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_endpoint_ai_contracts() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_ai_contracts.py"
    spec = importlib.util.spec_from_file_location("endpoint_ai_contracts", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_endpoint_status_contracts() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_status_contracts.py"
    spec = importlib.util.spec_from_file_location("endpoint_status_contracts", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_endpoint_review_workflow_contracts() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_review_workflow_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "endpoint_review_workflow_contracts",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_endpoint_conversion_workflow_contracts() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_conversion_workflow_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "endpoint_conversion_workflow_contracts",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_endpoint_report_evidence_contracts() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_report_evidence_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "endpoint_report_evidence_contracts",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_endpoint_candidate_state_contracts() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_candidate_state_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "endpoint_candidate_state_contracts",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_endpoint_certification_gate_passes_current_repository_contract() -> None:
    module = _load_endpoint_certification_gate()

    assert module.main() == 0


def test_endpoint_certification_gate_blocks_missing_capability() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
        "certification_status": "certified",
        "when_to_use": "Use for internal review recording.",
        "when_not_to_use": (
            "Do not use as Gateway contract, Workbench product proof, or "
            "supported-feature promotion."
        ),
        "error_examples": ["403 returns product-safe Problem Details."],
        "openapi_evidence": "scripts/openapi_quality_gate.py validates the operation.",
    }

    errors = module._validate_implemented_endpoint_posture(endpoint)

    assert (
        "('POST', '/api/v1/idea-candidates/{candidateId}/review-actions'): "
        "implemented endpoint must name at least one idea.* capability"
    ) in errors


def test_endpoint_certification_gate_blocks_weak_unsupported_boundary() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
        "certification_status": "certified",
        "when_to_use": "Use with idea.review.record capability.",
        "when_not_to_use": "Do not use as a supported-feature promotion.",
        "error_examples": ["403 returns product-safe Problem Details."],
        "openapi_evidence": "scripts/openapi_quality_gate.py validates the operation.",
    }

    errors = module._validate_implemented_endpoint_posture(endpoint)

    assert (
        "('POST', '/api/v1/idea-candidates/{candidateId}/review-actions'): "
        "when_not_to_use must explicitly preserve `Gateway` boundary"
    ) in errors
    assert (
        "('POST', '/api/v1/idea-candidates/{candidateId}/review-actions'): "
        "when_not_to_use must explicitly preserve `Workbench` boundary"
    ) in errors


def test_endpoint_certification_gate_blocks_missing_operation_event_evidence() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
        "certification_status": "certified",
        "when_to_use": "Use with idea.review.record capability.",
        "when_not_to_use": (
            "Do not use as Gateway contract, Workbench product proof, or "
            "supported-feature promotion."
        ),
        "error_examples": ["403 returns product-safe Problem Details."],
        "test_evidence": [
            "tests/integration/test_review_workflow_api.py::test_review_action_api_persists_suppression_with_audit_posture"
        ],
        "openapi_evidence": "scripts/openapi_quality_gate.py validates the operation.",
    }

    errors = module._validate_implemented_endpoint_posture(endpoint)

    assert (
        "('POST', '/api/v1/idea-candidates/{candidateId}/review-actions'): "
        "implemented endpoint must reference bounded operation-event test evidence"
    ) in errors


def test_endpoint_certification_gate_blocks_missing_integration_behavior_evidence() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = _certified_endpoint(
        test_evidence=[
            "tests/unit/test_security_caller_context.py::test_permission_denied_response_is_product_safe",
            "tests/integration/test_api_operation_events.py::test_signal_and_candidate_persistence_emit_bounded_operation_events",
        ]
    )

    errors = module._validate_implemented_endpoint_test_pyramid(
        ("POST", "/api/v1/example"), endpoint["test_evidence"]
    )

    assert errors == [
        "('POST', '/api/v1/example'): implemented endpoint must reference at least one "
        "integration API behavior test"
    ]


def test_endpoint_certification_gate_blocks_missing_negative_or_degraded_evidence() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = _certified_endpoint(
        test_evidence=[
            "tests/integration/test_high_cash_signal_api.py::test_high_cash_api_creates_candidate_from_source_owned_evidence",
            "tests/integration/test_api_operation_events.py::test_signal_and_candidate_persistence_emit_bounded_operation_events",
        ]
    )

    errors = module._validate_implemented_endpoint_test_pyramid(
        ("POST", "/api/v1/example"), endpoint["test_evidence"]
    )

    assert errors == [
        "('POST', '/api/v1/example'): implemented endpoint must reference negative or "
        "degraded-path test evidence"
    ]


def test_endpoint_certification_gate_accepts_operation_event_evidence() -> None:
    from app.api.examples.review_workflow import build_review_action_response_examples

    module = _load_endpoint_certification_gate()
    review_contracts = _load_endpoint_review_workflow_contracts()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
        "certification_status": "certified",
        "when_to_use": "Use with idea.review.record capability.",
        "when_not_to_use": (
            "Do not use as Gateway contract, Workbench product proof, or "
            "supported-feature promotion."
        ),
        "error_examples": ["403 returns product-safe Problem Details."],
        "response_examples": [
            json.dumps(value) for value in build_review_action_response_examples().values()
        ],
        "test_evidence": [
            "tests/integration/test_review_workflow_api.py::test_review_action_api_requires_permission_and_valid_request",
            "tests/integration/test_api_operation_events.py::test_lifecycle_queue_review_and_feedback_emit_operation_events",
            review_contracts.REVIEW_ACTION_IDENTITY_REPLAY_TEST,
            review_contracts.REVIEW_ACTION_SUCCESS_CONTRACT_TEST,
        ],
        "openapi_evidence": "scripts/openapi_quality_gate.py validates the operation.",
    }

    errors = module._validate_implemented_endpoint_posture(endpoint)

    assert errors == []


def test_endpoint_certification_gate_blocks_missing_openapi_caller_context_publication() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = _certified_endpoint(
        test_evidence=[
            "tests/integration/test_high_cash_signal_api.py::test_high_cash_api_requires_signal_evaluation_capability",
            "tests/integration/test_api_operation_events.py::test_signal_and_candidate_persistence_emit_bounded_operation_events",
        ]
    )
    endpoint["method"] = "POST"
    endpoint["path"] = "/api/v1/example"
    openapi_spec = {
        "paths": {
            "/api/v1/example": {
                "post": {
                    "security": [],
                    "parameters": [
                        {"name": "X-Caller-Capabilities", "in": "header"},
                        {"name": "X-Lotus-Trusted-Caller-Context", "in": "header"},
                    ],
                }
            }
        }
    }

    errors = module._validate_implemented_endpoint_posture(endpoint, openapi_spec)

    assert (
        "('POST', '/api/v1/example'): OpenAPI must publish Lotus caller-context security"
    ) in errors
    assert (
        "('POST', '/api/v1/example'): OpenAPI must publish `x-lotus-caller-context` requirements"
    ) in errors


def test_endpoint_certification_gate_accepts_openapi_caller_context_publication() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = _certified_endpoint(
        test_evidence=[
            "tests/integration/test_high_cash_signal_api.py::test_high_cash_api_requires_signal_evaluation_capability",
            "tests/integration/test_api_operation_events.py::test_signal_and_candidate_persistence_emit_bounded_operation_events",
        ]
    )
    endpoint["method"] = "POST"
    endpoint["path"] = "/api/v1/example"
    openapi_spec = {
        "paths": {
            "/api/v1/example": {
                "post": {
                    "security": [{"LotusCallerContext": []}],
                    "x-lotus-caller-context": {
                        "requiredCapabilities": ["idea.example.read"],
                        "trustedCallerContextProvenance": "trusted ingress required",
                    },
                    "parameters": [
                        {
                            "name": "X-Caller-Capabilities",
                            "in": "header",
                            "description": "caller capabilities",
                        },
                        {
                            "name": "X-Lotus-Trusted-Caller-Context",
                            "in": "header",
                            "description": "trusted provenance",
                        },
                    ],
                }
            }
        }
    }

    errors = module._validate_implemented_endpoint_posture(endpoint, openapi_spec)

    assert errors == []


def test_endpoint_certification_gate_accepts_bounded_gateway_publication_boundary() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = {
        "method": "GET",
        "path": "/api/v1/review-queues/advisor",
        "certification_status": "certified",
        "when_to_use": "Use with idea.review.queue.read capability.",
        "when_not_to_use": (
            "Read-only Gateway publication exists through lotus-gateway "
            "GET /api/v1/ideas/review-queues/advisor. Do not use as a durable "
            "queue store, Workbench product proof, data-product certification proof, "
            "PM/compliance/operator queue surface, client-ready publication, or "
            "supported-feature promotion."
        ),
        "error_examples": ["403 returns product-safe Problem Details."],
        "test_evidence": [
            "tests/integration/test_review_queue_api.py::test_review_queue_api_requires_permission",
            "tests/integration/test_api_operation_events.py::test_lifecycle_queue_review_and_feedback_emit_operation_events",
        ],
        "openapi_evidence": "scripts/openapi_quality_gate.py validates the operation.",
    }

    errors = module._validate_implemented_endpoint_posture(endpoint)

    assert errors == []


def test_endpoint_certification_gate_blocks_stale_gateway_contract_denial() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = {
        "method": "GET",
        "path": "/api/v1/review-queues/advisor",
        "certification_status": "certified",
        "when_to_use": "Use with idea.review.queue.read capability.",
        "when_not_to_use": (
            "Do not use as a durable queue store, scoped Workbench product surface, "
            "Gateway contract, data-product certification proof, or "
            "supported-feature promotion."
        ),
        "error_examples": ["403 returns product-safe Problem Details."],
        "test_evidence": [
            "tests/integration/test_api_operation_events.py::test_lifecycle_queue_review_and_feedback_emit_operation_events"
        ],
        "openapi_evidence": "scripts/openapi_quality_gate.py validates the operation.",
    }

    errors = module._validate_implemented_endpoint_posture(endpoint)

    assert (
        "('GET', '/api/v1/review-queues/advisor'): when_not_to_use must name the "
        "bounded read-only Gateway publication route instead of a generic Gateway "
        "contract denial"
    ) in errors


def test_endpoint_certification_gate_blocks_unimplemented_gateway_publication_claim() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
        "certification_status": "certified",
        "when_to_use": "Use with idea.review.record capability.",
        "when_not_to_use": (
            "Read-only Gateway publication exists through lotus-gateway "
            "GET /api/v1/ideas/review-actions. Do not use as Workbench product proof, "
            "data-product certification proof, client-ready publication, or "
            "supported-feature promotion."
        ),
        "error_examples": ["403 returns product-safe Problem Details."],
        "test_evidence": [
            "tests/integration/test_api_operation_events.py::test_lifecycle_queue_review_and_feedback_emit_operation_events"
        ],
        "openapi_evidence": "scripts/openapi_quality_gate.py validates the operation.",
    }

    errors = module._validate_implemented_endpoint_posture(endpoint)

    assert (
        "('POST', '/api/v1/idea-candidates/{candidateId}/review-actions'): only "
        "endpoints with implemented bounded Gateway publication may cite "
        "lotus-gateway publication"
    ) in errors


def test_endpoint_certification_gate_blocks_missing_signal_source_contract_example() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = _certified_endpoint(
        test_evidence=[
            "tests/integration/test_underperformance_signal_api.py::test_underperformance_signal_api_rejects_wrong_source_contract",
            "tests/integration/test_api_operation_events.py::test_underperformance_signal_api_emits_bounded_operation_event",
        ]
    )
    endpoint["path"] = "/api/v1/idea-signals/underperformance/evaluate"

    errors = module.validate_signal_source_contract_error_examples(endpoint)

    assert errors == [
        "('POST', '/api/v1/idea-signals/underperformance/evaluate'): "
        "caller-supplied signal endpoint must document source-ref contract mismatch behavior"
    ]


def test_endpoint_certification_gate_blocks_unrelated_signal_source_contract_fields() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = _certified_endpoint(
        test_evidence=[
            "tests/integration/test_underperformance_signal_api.py::test_underperformance_signal_api_rejects_wrong_source_contract",
            "tests/integration/test_api_operation_events.py::test_underperformance_signal_api_emits_bounded_operation_event",
        ]
    )
    endpoint["path"] = "/api/v1/idea-signals/underperformance/evaluate"
    endpoint["error_examples"] = [
        "403 returns product-safe Problem Details.",
        (
            "400 returns product-safe Problem Details when drawdownRef "
            "sourceSystem/productId does not match the governed Risk source contract."
        ),
    ]

    errors = module.validate_signal_source_contract_error_examples(endpoint)

    assert (
        "('POST', '/api/v1/idea-signals/underperformance/evaluate'): "
        "source-ref contract error example must mention `performanceRef`"
    ) in errors
    assert (
        "('POST', '/api/v1/idea-signals/underperformance/evaluate'): "
        "source-ref contract error example mentions unrelated fields: drawdownRef"
    ) in errors


def test_endpoint_certification_gate_accepts_signal_source_contract_example() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = _certified_endpoint(
        test_evidence=[
            "tests/integration/test_underperformance_signal_api.py::test_underperformance_signal_api_rejects_wrong_source_contract",
            "tests/integration/test_api_operation_events.py::test_underperformance_signal_api_emits_bounded_operation_event",
        ]
    )
    endpoint["path"] = "/api/v1/idea-signals/underperformance/evaluate"
    endpoint["error_examples"] = [
        "403 returns product-safe Problem Details.",
        (
            "400 returns product-safe Problem Details when performanceRef "
            "sourceSystem/productId does not match the governed Performance source contract."
        ),
    ]

    errors = module.validate_signal_source_contract_error_examples(endpoint)

    assert errors == []


def test_endpoint_certification_gate_validates_test_references() -> None:
    module = _load_endpoint_certification_gate()

    missing_file = module._validate_test_reference(
        ("GET", "/metadata"),
        "tests/integration/test_missing.py::test_metadata_endpoint",
    )
    missing_test = module._validate_test_reference(
        ("GET", "/metadata"),
        "tests/e2e/test_smoke.py::test_missing_endpoint",
    )

    assert "('GET', '/metadata'): test_evidence file does not exist" in missing_file[0]
    assert (
        "('GET', '/metadata'): test_evidence test does not exist: "
        "tests/e2e/test_smoke.py::test_missing_endpoint"
    ) in missing_test


def test_endpoint_certification_gate_validates_json_examples() -> None:
    module = _load_endpoint_certification_gate()

    errors = module._parse_json_examples(
        operation=("POST", "/api/v1/example"),
        field="response_examples",
        examples=['{"supportedFeaturePromoted": false}', '{"broken": }'],
    )

    assert "('POST', '/api/v1/example'): response_examples[1] must be valid JSON" in errors[0]


def test_endpoint_certification_gate_represents_implemented_uncertified_truth() -> None:
    module = _load_endpoint_certification_gate()

    assert "implemented_not_certified" in module.ALLOWED_CERTIFICATION_STATUSES
    assert "implemented_not_certified" in module.IMPLEMENTED_OPERATION_STATUSES


def test_endpoint_certification_gate_blocks_weak_implemented_uncertified_contract() -> None:
    module = _load_endpoint_certification_gate()
    endpoint = _implemented_uncertified_endpoint()
    endpoint.update(
        {
            "when_to_use": "Use for a sensitive mutation.",
            "when_not_to_use": "Do not promote.",
            "error_examples": ["400 invalid request."],
            "test_evidence": [],
            "openapi_evidence": "none",
        }
    )

    errors = module._validate_implemented_endpoint_posture(endpoint, {"paths": {}})

    assert any("must name at least one idea.* capability" in error for error in errors)
    assert any("must explicitly preserve `Gateway` boundary" in error for error in errors)
    assert any("must document product-safe 403 behavior" in error for error in errors)
    assert any("must reference bounded operation-event test evidence" in error for error in errors)
    assert any("integration API behavior test" in error for error in errors)
    assert any("negative or degraded-path test evidence" in error for error in errors)

    endpoint["when_to_use"] = "Use with idea.data-lifecycle.manage capability."
    caller_context_errors = module._validate_implemented_endpoint_posture(
        endpoint,
        {"paths": {}},
    )
    assert any(
        "missing OpenAPI operation for caller-context publication" in error
        for error in caller_context_errors
    )


def test_endpoint_status_contract_requires_blockers_and_truthful_posture() -> None:
    module = _load_endpoint_status_contracts()
    endpoint = _implemented_uncertified_endpoint()
    endpoint["certification_blockers"] = []
    endpoint["response_examples"] = [
        '{"certificationStatus":"certified","supportedFeaturePromoted":true}'
    ]

    errors = module.validate_endpoint_status_contract(endpoint, {"paths": {}})

    assert any("must declare certification_blockers" in error for error in errors)
    assert any("response_examples must preserve" in error for error in errors)
    assert any("OpenAPI success examples must preserve" in error for error in errors)


def test_endpoint_status_contract_accepts_explicit_uncertified_posture() -> None:
    module = _load_endpoint_status_contracts()
    endpoint = _implemented_uncertified_endpoint()
    openapi_spec = {
        "paths": {
            endpoint["path"]: {
                "post": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "example": {
                                        "certificationStatus": "not_certified",
                                        "supportedFeaturePromoted": False,
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    assert module.validate_endpoint_status_contract(endpoint, openapi_spec) == []


def test_endpoint_certification_gate_blocks_stale_attested_ai_success_truth() -> None:
    module = _load_endpoint_ai_contracts()
    endpoint = _ai_evaluation_endpoint()
    endpoint["when_to_use"] = (
        "Use with idea.ai-explanation.evaluate capability. Production-like profiles "
        "currently reject workflow output."
    )
    endpoint["test_evidence"] = []

    errors = module.validate_ai_evaluation_success_contract(endpoint)

    assert any("must not reject verified attested workflow output" in error for error in errors)
    assert any(
        "must cite the attested AI API success integration test" in error for error in errors
    )
    assert any("complete AI evaluation publication contract test" in error for error in errors)


def test_endpoint_certification_gate_requires_every_named_ai_success_mode() -> None:
    module = _load_endpoint_ai_contracts()
    endpoint = _ai_evaluation_endpoint()
    openapi_spec = _ai_evaluation_openapi()
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples.pop("deterministicFallback")

    errors = module.validate_ai_evaluation_success_contract(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate'): "
            "OpenAPI 200 examples must exactly match every named code-owned AI evaluation "
            "success mode"
        )
    ]


def test_endpoint_certification_gate_blocks_ai_success_safety_field_drift() -> None:
    module = _load_endpoint_ai_contracts()
    endpoint = _ai_evaluation_endpoint()
    response_examples = endpoint["response_examples"]
    assert isinstance(response_examples, list)
    assert all(isinstance(value, str) for value in response_examples)
    examples = [json.loads(value) for value in response_examples]
    mutations = []

    missing_control = deepcopy(examples)
    missing_control[0].pop("metadataEnvelopeVersion")
    mutations.append(missing_control)

    missing_grounding = deepcopy(examples)
    missing_grounding[0]["verifiedOutput"].pop("claimGroundingPolicyVersion")
    mutations.append(missing_grounding)

    blocked_narrative_drift = deepcopy(examples)
    blocked_narrative_drift[3]["explanationText"] = "Provider-authored rejected narrative"
    mutations.append(blocked_narrative_drift)

    fallback_authority_drift = deepcopy(examples)
    fallback_authority_drift[2]["grantsDownstreamAuthority"] = True
    mutations.append(fallback_authority_drift)

    for mutation in mutations:
        changed = deepcopy(endpoint)
        changed["response_examples"] = [json.dumps(value) for value in mutation]
        errors = module.validate_ai_evaluation_success_contract(changed)
        assert any("response_examples must exactly match" in error for error in errors)


def test_endpoint_certification_gate_accepts_complete_ai_success_truth() -> None:
    module = _load_endpoint_ai_contracts()

    assert (
        module.validate_ai_evaluation_success_contract(
            _ai_evaluation_endpoint(),
            _ai_evaluation_openapi(),
        )
        == []
    )


def test_endpoint_certification_gate_blocks_ai_readiness_publication_drift() -> None:
    import json

    module = _load_endpoint_ai_contracts()
    endpoint = _ai_readiness_endpoint()
    ledger_example = json.loads(str(endpoint["response_examples"][0]))
    ledger_example.pop("claimGroundingAvailable")
    endpoint["response_examples"] = [json.dumps(ledger_example)]
    endpoint["test_evidence"] = []
    openapi_spec = _ai_readiness_openapi()
    openapi_example = openapi_spec["paths"][endpoint["path"]]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["example"]
    openapi_example["certificationBlockers"].remove("model_risk_dashboard_runtime_proof_missing")

    errors = module.validate_ai_readiness_success_contract(endpoint, openapi_spec)

    assert any("response_examples must exactly match" in error for error in errors)
    assert any("test_evidence must cite" in error for error in errors)
    assert any("OpenAPI success example must exactly match" in error for error in errors)


def test_endpoint_certification_gate_accepts_complete_ai_readiness_publication() -> None:
    module = _load_endpoint_ai_contracts()

    assert (
        module.validate_ai_readiness_success_contract(
            _ai_readiness_endpoint(),
            _ai_readiness_openapi(),
        )
        == []
    )


def test_endpoint_certification_gate_requires_every_feedback_success_mode() -> None:
    from app.api.examples.review_workflow import build_feedback_response_examples
    from app.main import app

    module = _load_endpoint_review_workflow_contracts()
    expected = build_feedback_response_examples()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/feedback",
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.FEEDBACK_IDENTITY_REPLAY_TEST,
            module.FEEDBACK_SUCCESS_CONTRACT_TEST,
        ],
    }
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples.pop("replayed")

    errors = module.validate_feedback_success_contract(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/idea-candidates/{candidateId}/feedback'): OpenAPI 200 "
            "examples must exactly match every named code-owned feedback success mode"
        )
    ]


def test_endpoint_certification_gate_blocks_feedback_ledger_and_test_drift() -> None:
    from app.api.examples.review_workflow import build_feedback_response_examples

    module = _load_endpoint_review_workflow_contracts()
    expected = build_feedback_response_examples()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/feedback",
        "response_examples": [json.dumps(expected["accepted"])],
        "test_evidence": [],
    }

    errors = module.validate_feedback_success_contract(endpoint)

    assert any("response_examples must exactly match" in error for error in errors)
    assert any("cross-key feedback replay integration test" in error for error in errors)
    assert any("feedback success publication contract test" in error for error in errors)


def test_endpoint_certification_gate_requires_every_review_action_success_mode() -> None:
    from app.api.examples.review_workflow import build_review_action_response_examples
    from app.main import app

    module = _load_endpoint_review_workflow_contracts()
    expected = build_review_action_response_examples()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.REVIEW_ACTION_IDENTITY_REPLAY_TEST,
            module.REVIEW_ACTION_SUCCESS_CONTRACT_TEST,
        ],
    }
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples["accepted"]["value"]["reviewDecision"].pop("snoozedUntilUtc")

    errors = module.validate_review_action_success_contract(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/idea-candidates/{candidateId}/review-actions'): OpenAPI "
            "200 examples must exactly match every named code-owned review-action success mode"
        )
    ]


def test_endpoint_certification_gate_blocks_review_action_ledger_and_test_drift() -> None:
    from app.api.examples.review_workflow import build_review_action_response_examples

    module = _load_endpoint_review_workflow_contracts()
    expected = build_review_action_response_examples()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
        "response_examples": [json.dumps(expected["accepted"])],
        "test_evidence": [],
    }

    errors = module.validate_review_action_success_contract(endpoint)

    assert any("response_examples must exactly match" in error for error in errors)
    assert any("cross-key review-action replay integration test" in error for error in errors)
    assert any("review-action success publication contract test" in error for error in errors)


def test_endpoint_certification_gate_requires_every_conversion_intent_success_mode() -> None:
    from app.api.examples.conversion_workflow import (
        build_conversion_intent_response_examples,
    )
    from app.main import app

    module = _load_endpoint_conversion_workflow_contracts()
    expected = build_conversion_intent_response_examples()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/conversion-intents",
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.CONVERSION_INTENT_REPLAY_TEST,
            module.CONVERSION_INTENT_SUCCESS_CONTRACT_TEST,
        ],
    }
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples.pop("replayed")

    errors = module.validate_conversion_intent_success_contract(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/idea-candidates/{candidateId}/conversion-intents'): "
            "OpenAPI 200 examples must exactly match every named code-owned "
            "conversion-intent success mode"
        )
    ]


def test_endpoint_certification_gate_blocks_conversion_intent_ledger_and_test_drift() -> None:
    from app.api.examples.conversion_workflow import (
        build_conversion_intent_response_examples,
    )

    module = _load_endpoint_conversion_workflow_contracts()
    expected = build_conversion_intent_response_examples()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/conversion-intents",
        "response_examples": [json.dumps(expected["accepted"])],
        "test_evidence": [],
    }

    errors = module.validate_conversion_intent_success_contract(endpoint)

    assert any("response_examples must exactly match" in error for error in errors)
    assert any("idempotent conversion-intent replay integration test" in error for error in errors)
    assert any("conversion-intent success publication contract test" in error for error in errors)


def test_endpoint_certification_gate_requires_every_conversion_outcome_success_mode() -> None:
    from app.api.examples.conversion_workflow import (
        build_conversion_outcome_response_examples,
    )
    from app.main import app

    module = _load_endpoint_conversion_workflow_contracts()
    expected = build_conversion_outcome_response_examples()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/conversion-intents/{conversionIntentId}/outcomes",
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.CONVERSION_OUTCOME_REPLAY_TEST,
            module.CONVERSION_OUTCOME_SUCCESS_CONTRACT_TEST,
        ],
    }
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples["accepted"]["value"]["conversionOutcome"].pop("correctionReason")

    errors = module.validate_conversion_outcome_success_contract(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/conversion-intents/{conversionIntentId}/outcomes'): "
            "OpenAPI 200 examples must exactly match every named code-owned "
            "conversion-outcome success mode"
        )
    ]


def test_endpoint_certification_gate_blocks_conversion_outcome_ledger_and_test_drift() -> None:
    from app.api.examples.conversion_workflow import (
        build_conversion_outcome_response_examples,
    )

    module = _load_endpoint_conversion_workflow_contracts()
    expected = build_conversion_outcome_response_examples()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/conversion-intents/{conversionIntentId}/outcomes",
        "response_examples": [json.dumps(expected["accepted"])],
        "test_evidence": [],
    }

    errors = module.validate_conversion_outcome_success_contract(endpoint)

    assert any("response_examples must exactly match" in error for error in errors)
    assert any("cross-key conversion-outcome replay integration test" in error for error in errors)
    assert any("conversion-outcome success publication contract test" in error for error in errors)


def test_endpoint_certification_gate_requires_every_report_evidence_pack_success_mode() -> None:
    from app.api.examples.report_evidence import (
        build_report_evidence_pack_response_examples,
    )
    from app.main import app

    module = _load_endpoint_report_evidence_contracts()
    expected = build_report_evidence_pack_response_examples()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.REPORT_EVIDENCE_PACK_REPLAY_TEST,
            module.REPORT_EVIDENCE_PACK_SUCCESS_CONTRACT_TEST,
        ],
    }
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples["accepted"]["value"]["reportEvidencePack"]["createsArchiveRecord"] = True

    errors = module.validate_report_evidence_pack_success_contract(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs'): "
            "OpenAPI 200 examples must exactly match every named code-owned "
            "report-evidence-pack success mode"
        )
    ]


def test_endpoint_certification_gate_blocks_report_evidence_ledger_and_test_drift() -> None:
    from app.api.examples.report_evidence import (
        build_report_evidence_pack_response_examples,
    )

    module = _load_endpoint_report_evidence_contracts()
    expected = build_report_evidence_pack_response_examples()
    endpoint = {
        "method": "POST",
        "path": "/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
        "response_examples": [json.dumps(expected["accepted"])],
        "test_evidence": [],
    }

    errors = module.validate_report_evidence_pack_success_contract(endpoint)

    assert any("response_examples must exactly match" in error for error in errors)
    assert any(
        "idempotent report-evidence-pack replay integration test" in error for error in errors
    )
    assert any(
        "report-evidence-pack success publication contract test" in error for error in errors
    )


def _certified_endpoint(*, test_evidence: list[str]) -> dict[str, object]:
    return {
        "method": "POST",
        "path": "/api/v1/example",
        "certification_status": "certified",
        "owner": "lotus-idea owners",
        "purpose": "Example endpoint.",
        "when_to_use": "Use with idea.example.read capability.",
        "when_not_to_use": "Do not use as Gateway, Workbench, or supported-feature promotion.",
        "request_examples": ["{}"],
        "response_examples": ["{}"],
        "error_examples": ["403 returns product-safe Problem Details."],
        "test_evidence": test_evidence,
        "openapi_evidence": "scripts/openapi_quality_gate.py validates this endpoint.",
    }


def _ai_evaluation_endpoint() -> dict[str, object]:
    from app.api.examples.ai_explanation import build_ai_explanation_evaluation_examples

    return {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate",
        "purpose": "Verify workflow output with a verified Lotus AI run attestation.",
        "when_to_use": (
            "Use with idea.ai-explanation.evaluate and verified Lotus AI run attestation."
        ),
        "response_examples": [
            json.dumps(value) for value in build_ai_explanation_evaluation_examples().values()
        ],
        "test_evidence": [
            "tests/integration/test_attested_ai_governance_api.py::"
            "test_api_accepts_signed_bound_lotus_ai_output",
            "tests/unit/api_examples/test_ai_explanation.py::"
            "test_ai_explanation_success_examples_match_ledger_and_openapi",
        ],
    }


def _ai_evaluation_openapi() -> dict[str, Any]:
    from app.api.examples.ai_explanation import build_ai_explanation_evaluation_examples

    return {
        "paths": {
            "/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate": {
                "post": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "examples": {
                                        name: {"value": value}
                                        for name, value in (
                                            build_ai_explanation_evaluation_examples().items()
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }


def _implemented_uncertified_endpoint() -> dict[str, object]:
    return {
        "method": "POST",
        "path": "/api/v1/data-lifecycle/candidates/{candidateId}/actions",
        "certification_status": "implemented_not_certified",
        "certification_blockers": [
            "live_bank_lifecycle_authority_proof_missing",
            "production_archive_trust_and_store_proof_missing",
        ],
        "owner": "lotus-idea privacy and records operations",
        "purpose": "Apply a governed lifecycle action.",
        "when_to_use": "Use with idea.data-lifecycle.manage capability.",
        "when_not_to_use": ("Do not use as Gateway, Workbench, or supported-feature promotion."),
        "request_examples": ["{}"],
        "response_examples": [
            '{"certificationStatus":"not_certified","supportedFeaturePromoted":false}'
        ],
        "error_examples": ["403 returns product-safe Problem Details."],
        "test_evidence": [
            "tests/integration/test_data_lifecycle_api.py::"
            "test_data_lifecycle_api_requires_role_capability_and_exact_tenant",
            "tests/integration/data_lifecycle/test_operation_events.py::"
            "test_data_lifecycle_api_emits_bounded_permission_event",
        ],
        "openapi_evidence": "scripts/openapi_quality_gate.py validates this endpoint.",
    }


def _ai_readiness_endpoint() -> dict[str, Any]:
    from app.api.ai_governance_models import build_ai_explanation_readiness_response

    response = build_ai_explanation_readiness_response().model_dump_json(by_alias=True)
    return {
        "method": "GET",
        "path": "/api/v1/ai-explanations/readiness",
        "response_examples": [response],
        "test_evidence": [
            "tests/unit/test_ai_explanation_readiness.py::"
            "test_ai_explanation_readiness_published_examples_match_runtime_contract"
        ],
    }


def _ai_readiness_openapi() -> dict[str, Any]:
    from app.api.ai_governance_models import build_ai_explanation_readiness_response

    response = build_ai_explanation_readiness_response().model_dump(mode="json", by_alias=True)
    return {
        "paths": {
            "/api/v1/ai-explanations/readiness": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "example": response,
                                }
                            }
                        }
                    }
                }
            }
        }
    }


def test_endpoint_certification_gate_requires_every_candidate_lifecycle_success_mode() -> None:
    from app.api.examples.candidate_state import (
        build_candidate_lifecycle_response_examples,
    )
    from app.main import app

    module = _load_endpoint_candidate_state_contracts()
    expected = build_candidate_lifecycle_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.CANDIDATE_LIFECYCLE_OPERATION[1],
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.CANDIDATE_LIFECYCLE_BEHAVIOR_TEST,
            module.CANDIDATE_LIFECYCLE_SUCCESS_CONTRACT_TEST,
        ],
    }
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples.pop("replayed")

    errors = module.validate_candidate_lifecycle_success_contract(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/idea-candidates/{candidateId}/lifecycle-transitions'): "
            "OpenAPI 200 examples must exactly match every named code-owned "
            "candidate-lifecycle success mode"
        )
    ]


def test_endpoint_certification_gate_blocks_candidate_evidence_replay_openapi_drift() -> None:
    from app.api.examples.candidate_state import (
        build_candidate_evidence_replay_response_examples,
    )
    from app.main import app

    module = _load_endpoint_candidate_state_contracts()
    expected = build_candidate_evidence_replay_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.CANDIDATE_EVIDENCE_REPLAY_OPERATION[1],
        "response_examples": [json.dumps(value) for value in expected.values()],
        "test_evidence": [
            module.CANDIDATE_EVIDENCE_REPLAY_MATCHED_TEST,
            module.CANDIDATE_EVIDENCE_REPLAY_COMPARISON_TEST,
            module.CANDIDATE_EVIDENCE_REPLAY_EXPIRED_TEST,
            module.CANDIDATE_EVIDENCE_REPLAY_SUCCESS_CONTRACT_TEST,
        ],
    }
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][endpoint["path"]]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]
    examples["staleSource"]["value"]["currentEvidenceHash"] = "sha256:unexpected"

    errors = module.validate_candidate_evidence_replay_success_contract(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/idea-candidates/{candidateId}/evidence-replay'): "
            "OpenAPI 200 examples must exactly match every named code-owned "
            "candidate-evidence-replay success mode"
        )
    ]


def test_endpoint_certification_gate_blocks_candidate_evidence_replay_ledger_and_test_drift() -> (
    None
):
    from app.api.examples.candidate_state import (
        build_candidate_evidence_replay_response_examples,
    )

    module = _load_endpoint_candidate_state_contracts()
    expected = build_candidate_evidence_replay_response_examples()
    endpoint = {
        "method": "POST",
        "path": module.CANDIDATE_EVIDENCE_REPLAY_OPERATION[1],
        "response_examples": [
            json.dumps(expected["matched"]),
            json.dumps(expected["hashMismatch"]),
        ],
        "test_evidence": [module.CANDIDATE_EVIDENCE_REPLAY_MATCHED_TEST],
    }

    errors = module.validate_candidate_evidence_replay_success_contract(endpoint)

    assert any("response_examples must exactly match" in error for error in errors)
    assert any("hash-mismatch and stale-source" in error for error in errors)
    assert any("expired candidate-evidence-replay integration test" in error for error in errors)
    assert any("success publication contract test" in error for error in errors)
