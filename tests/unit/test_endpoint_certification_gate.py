from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType


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
            "tests/integration/test_review_workflow_api.py::test_review_action_api_requires_permission_and_valid_request",
            "tests/integration/test_api_operation_events.py::test_lifecycle_queue_review_and_feedback_emit_operation_events",
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
    endpoint = _attested_ai_endpoint()
    endpoint["when_to_use"] = (
        "Use with idea.ai-explanation.evaluate capability. Production-like profiles "
        "currently reject workflow output."
    )
    endpoint["response_examples"] = [
        '{"executionProvenancePosture":"unattested_local_test_fixture",'
        '"lotusAiRuntimeExecuted":false,"grantsDownstreamAuthority":false,'
        '"supportedFeaturePromoted":false}'
    ]
    endpoint["test_evidence"] = []

    errors = module.validate_ai_attested_success_mode(endpoint)

    assert any("must not reject verified attested workflow output" in error for error in errors)
    assert any("must include verified attested AI success posture" in error for error in errors)
    assert any(
        "must cite the attested AI API success integration test" in error for error in errors
    )


def test_endpoint_certification_gate_requires_named_openapi_attested_success_mode() -> None:
    module = _load_endpoint_ai_contracts()
    endpoint = _attested_ai_endpoint()
    openapi_spec = {
        "paths": {
            endpoint["path"]: {
                "post": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "examples": {
                                        "unattestedLocalTestFixture": {
                                            "value": {
                                                "executionProvenancePosture": (
                                                    "unattested_local_test_fixture"
                                                ),
                                                "lotusAiRuntimeExecuted": False,
                                                "grantsDownstreamAuthority": False,
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
        }
    }

    errors = module.validate_ai_attested_success_mode(endpoint, openapi_spec)

    assert errors == [
        (
            "('POST', '/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate'): "
            "OpenAPI 200 examples must include verified attested AI success"
        )
    ]


def test_endpoint_certification_gate_accepts_complete_attested_ai_success_truth() -> None:
    module = _load_endpoint_ai_contracts()
    endpoint = _attested_ai_endpoint()
    attested = {
        "executionProvenancePosture": "lotus_ai_attestation_verified",
        "lotusAiRuntimeExecuted": True,
        "grantsDownstreamAuthority": False,
        "supportedFeaturePromoted": False,
    }
    openapi_spec = {
        "paths": {
            endpoint["path"]: {
                "post": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "examples": {
                                        "unattestedLocalTestFixture": {"value": {}},
                                        "verifiedAttestedOutput": {"value": attested},
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    assert module.validate_ai_attested_success_mode(endpoint, openapi_spec) == []


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


def _attested_ai_endpoint() -> dict[str, object]:
    return {
        "method": "POST",
        "path": "/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate",
        "purpose": "Verify workflow output with a verified Lotus AI run attestation.",
        "when_to_use": (
            "Use with idea.ai-explanation.evaluate and verified Lotus AI run attestation."
        ),
        "response_examples": [
            '{"executionProvenancePosture":"lotus_ai_attestation_verified",'
            '"lotusAiRuntimeExecuted":true,"grantsDownstreamAuthority":false,'
            '"supportedFeaturePromoted":false}'
        ],
        "test_evidence": [
            "tests/integration/test_attested_ai_governance_api.py::"
            "test_api_accepts_signed_bound_lotus_ai_output"
        ],
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
