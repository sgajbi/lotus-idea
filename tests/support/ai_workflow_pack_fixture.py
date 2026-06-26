from __future__ import annotations

from pathlib import Path


def write_lotus_ai_workflow_pack_fixture(tmp_path: Path) -> Path:
    lotus_ai_root = tmp_path / "lotus-ai"
    _write(
        lotus_ai_root / "src/app/services/workflow_pack_phase1_specs.py",
        """
IDEA_EXPLANATION_V1_SPEC = dict(
    pack_id="idea_explanation.pack",
    pack_family="idea_explanation",
    owner_repository="lotus-idea",
    owner_service="lotus-idea",
    primary_use_case="governed_idea_explanation",
    workflow_authority_owner="lotus-idea",
    source_authority_boundaries=("lotus-idea", "lotus-gateway"),
    supported_inputs=("redacted_evidence_packet", "explanation_request", "supportability"),
)
""",
    )
    _write(
        lotus_ai_root / "src/app/services/workflow_pack_registry_seed.py",
        """
from app.services.workflow_pack_phase1_specs import IDEA_EXPLANATION_V1_SPEC

_idea_explanation_v1_definition_refs = (
    "repo://lotus-idea/src/app/domain/ai_governance.py",
    "src/app/application/ai_governance.py",
    "src/app/api/ai_governance.py",
    "tests/unit/test_ai_governance.py",
)

NON_PROOF_BOUNDARIES = (
    "cannot create suitability approval",
    "client-ready publication",
    "supported-feature promotion",
)


class WorkflowPackExecutionMode:
    REVIEW_GATED = "review_gated"


class WorkflowPackActivationState:
    PILOT = "pilot"


IDEA_EXPLANATION_REGISTRATION = {
    "spec": IDEA_EXPLANATION_V1_SPEC,
    "execution_mode": WorkflowPackExecutionMode.REVIEW_GATED,
    "activation_state": WorkflowPackActivationState.PILOT,
    "definition_refs": _idea_explanation_v1_definition_refs,
    "non_proof_boundaries": NON_PROOF_BOUNDARIES,
}
""",
    )
    _write(
        lotus_ai_root / "src/app/services/workflow_pack_bindings.py",
        """
from app.services.workflow_pack_phase1_specs import IDEA_EXPLANATION_V1_SPEC

idea_explanation_pack_id = "idea_explanation.pack"


def _build_execution_binding_from_spec(spec):
    return {"pack_id": idea_explanation_pack_id, "spec": spec}


IDEA_EXPLANATION_BINDING = _build_execution_binding_from_spec(IDEA_EXPLANATION_V1_SPEC)
""",
    )
    _write(
        lotus_ai_root / "src/app/services/workflow_pack_queue_policy_catalog.py",
        """
def _review_support_idea_explanation_policy():
    return "queue-policy.idea-explanation.v1"
""",
    )
    _write(
        lotus_ai_root / "src/app/services/ai_surface_supportability.py",
        """
SUPPORTED_AI_SURFACES = {
    "idea_explanation.pack@v1": {"authority": "lotus-idea"},
}
""",
    )
    _write(
        lotus_ai_root / "tests/unit/test_workflow_pack_registry.py",
        """
def test_registry_contains_idea_pack_contract():
    registration = {"pack_id": "idea_explanation.pack", "owner": "lotus-idea"}
    assert registration["pack_id"] == "idea_explanation.pack"
    assert registration["owner"] == "lotus-idea"
""",
    )
    _write(
        lotus_ai_root / "tests/unit/test_workflow_pack_bindings.py",
        """
def test_binding_contains_idea_pack_contract():
    binding = {"pack_id": "idea_explanation.pack"}
    assert binding["pack_id"] == "idea_explanation.pack"
""",
    )
    _write(
        lotus_ai_root / "tests/unit/test_workflow_pack_queue_policy_catalog.py",
        """
def test_queue_policy_contains_idea_pack_policy():
    policy_id = "queue-policy.idea-explanation.v1"
    assert policy_id == "queue-policy.idea-explanation.v1"
""",
    )
    _write(
        lotus_ai_root / "tests/unit/test_workflow_pack_runtime_status.py",
        """
def test_runtime_status_names_idea_pack_without_execution_claim():
    workflow_pack_id = "idea_explanation.pack@v1"
    assert workflow_pack_id == "idea_explanation.pack@v1"
""",
    )
    _write(
        lotus_ai_root / "tests/integration/test_workflow_pack_registry_api_contract.py",
        """
def test_registry_api_returns_default_registration_ref_for_idea_pack():
    response = {
        "pack_id": "idea_explanation.pack",
        "default_registration_ref": "workflow-pack:idea_explanation.pack@v1",
    }
    assert response["pack_id"] == "idea_explanation.pack"
    assert response["default_registration_ref"]
""",
    )
    return lotus_ai_root


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.lstrip(), encoding="utf-8")
