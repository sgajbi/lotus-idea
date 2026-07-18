from __future__ import annotations

from pathlib import Path

_BASE_WORKFLOW_PACK_FILES: tuple[tuple[str, str], ...] = (
    (
        "src/app/services/workflow_pack_phase1_specs.py",
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
    ),
    (
        "src/app/services/workflow_pack_registry_seed.py",
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
    ),
    (
        "src/app/services/workflow_pack_bindings.py",
        """
from app.services.workflow_pack_phase1_specs import IDEA_EXPLANATION_V1_SPEC

idea_explanation_pack_id = "idea_explanation.pack"


def _build_execution_binding_from_spec(spec):
    return {"pack_id": idea_explanation_pack_id, "spec": spec}


IDEA_EXPLANATION_BINDING = _build_execution_binding_from_spec(IDEA_EXPLANATION_V1_SPEC)
""",
    ),
    (
        "src/app/services/workflow_pack_queue_policy_catalog.py",
        """
def _review_support_idea_explanation_policy():
    return "queue-policy.idea-explanation.v1"
""",
    ),
    (
        "src/app/services/ai_surface_supportability.py",
        """
SUPPORTED_AI_SURFACES = {
    "idea_explanation.pack@v1": {"authority": "lotus-idea"},
}
""",
    ),
    (
        "tests/unit/test_workflow_pack_registry.py",
        """
def test_registry_contains_idea_pack_contract():
    registration = {"pack_id": "idea_explanation.pack", "owner": "lotus-idea"}
    assert registration["pack_id"] == "idea_explanation.pack"
    assert registration["owner"] == "lotus-idea"
""",
    ),
    (
        "tests/unit/test_workflow_pack_bindings.py",
        """
def test_binding_contains_idea_pack_contract():
    binding = {"pack_id": "idea_explanation.pack"}
    assert binding["pack_id"] == "idea_explanation.pack"
""",
    ),
    (
        "tests/unit/test_workflow_pack_queue_policy_catalog.py",
        """
def test_queue_policy_contains_idea_pack_policy():
    policy_id = "queue-policy.idea-explanation.v1"
    assert policy_id == "queue-policy.idea-explanation.v1"
""",
    ),
    (
        "tests/unit/test_workflow_pack_runtime_status.py",
        """
def test_runtime_status_names_idea_pack_without_execution_claim():
    workflow_pack_id = "idea_explanation.pack@v1"
    assert workflow_pack_id == "idea_explanation.pack@v1"
""",
    ),
    (
        "tests/integration/test_workflow_pack_registry_api_contract.py",
        """
def test_registry_api_returns_default_registration_ref_for_idea_pack():
    response = {
        "pack_id": "idea_explanation.pack",
        "default_registration_ref": "workflow-pack:idea_explanation.pack@v1",
    }
    assert response["pack_id"] == "idea_explanation.pack"
    assert response["default_registration_ref"]
""",
    ),
)

_RUNTIME_EXECUTION_WORKFLOW_PACK_FILES: tuple[tuple[str, str], ...] = (
    (
        "src/app/providers/idea_explanation_stub.py",
        """
def build_idea_explanation_stub_result(*, context_payload):
    return "draft", {
        "state": "REVIEW_REQUIRED",
        "scope": "advisor_and_reviewer_use_only",
        "human_review_required": True,
        "client_ready_publication": "BLOCKED",
        "downstream_authority": "BLOCKED",
    }
""",
    ),
    (
        "src/app/services/idea_explanation_guardrails.py",
        """
_FORBIDDEN_REQUESTED_OUTPUTS = {"client_ready_publication"}
_FORBIDDEN_TECHNICAL_KEYS = {"raw_prompt", "raw_provider_output"}


def validate_idea_explanation_payload(payload):
    redacted_evidence_packet = payload["redacted_evidence_packet"]
    evidence_content_hash = redacted_evidence_packet["evidence_content_hash"]
    assert evidence_content_hash.startswith("sha256:")
    requested_outputs = payload["explanation_request"]["requested_outputs"]
    assert requested_outputs
    supportability = payload["supportability"]
    assert supportability["client_ready_publication"] == "BLOCKED"
    assert supportability["human_review_required"] is True
    assert supportability["forbidden_actions"]
""",
    ),
    (
        "src/app/services/workflow_pack_execution.py",
        """
from app.services.idea_explanation_guardrails import validate_idea_explanation_payload


def execute(request):
    if request.pack_id == "idea_explanation.pack" and request.version == "v1":
        validate_idea_explanation_payload(request.task_request.context.payload)
""",
    ),
    (
        "src/app/providers/stub_text_provider.py",
        """
from app.providers.idea_explanation_stub import build_idea_explanation_stub_result


def generate(request):
    idea_explanation_result = build_idea_explanation_stub_result(
        context_payload=request.context.payload
    )
    if request.task_id == "explain.v1" and idea_explanation_result:
        return idea_explanation_result
""",
    ),
    (
        "src/app/repositories/memory_caller_policy_repository.py",
        """
LOTUS_IDEA_POLICY = dict(
    caller_app="lotus-idea",
    allowed_task_ids=["explain.v1"],
    allow_live_provider=False,
    allow_provider_control=False,
    restricted_tenant_ids=["tenant-sg-001"],
)
""",
    ),
    (
        "alembic/versions/0034_seed_lotus_idea_caller_policy.py",
        """
def upgrade():
    values = (
        'lotus-idea',
        '["tenant-sg-001"]',
        '["explain.v1"]',
        false,
        'RESTRICTED',
        '["tenant-sg-001"]',
    )
    assert values
""",
    ),
    (
        "tests/support/workflow_pack_fixtures.py",
        """
def idea_explanation_payload():
    return {"redacted_evidence_packet": {}, "explanation_request": {}, "supportability": {}}


def idea_explanation_workflow_pack_execution_request_json():
    return {"pack_id": "idea_explanation.pack"}
""",
    ),
    (
        "tests/unit/test_idea_explanation_guardrails.py",
        """
from tests.support.workflow_pack_fixtures import idea_explanation_payload


def test_accepts_source_safe_idea_explanation_payload():
    validate_idea_explanation_payload(idea_explanation_payload())
""",
    ),
    (
        "tests/unit/test_workflow_pack_execution.py",
        """
def test_execute_workflow_pack_records_review_gated_idea_explanation_output():
    assert workflow_authority_owner == "lotus-idea"
    structured_output = {
        "state": "REVIEW_REQUIRED",
        "client_ready_publication": "BLOCKED",
    }
    assert structured_output["client_ready_publication"] == "BLOCKED"


def test_validate_workflow_pack_execution_binding_runs_idea_explanation_guardrails():
    return True
""",
    ),
    (
        "tests/unit/test_workflow_pack_bindings.py",
        """
def test_get_workflow_pack_execution_binding_returns_idea_explanation_binding():
    binding.validate_task_request_payload(payload=idea_explanation_payload())
""",
    ),
    (
        "tests/unit/test_access_control_authorization.py",
        """
def test_authorize_lotus_idea_explain_request():
    request = dict(caller_app="lotus-idea", task_id="explain.v1")
    assert request
""",
    ),
    (
        "tests/unit/test_sqlalchemy_caller_policy_repository.py",
        """
def test_seeded_lotus_idea_policy_blocks_live_provider():
    class Policy:
        allow_live_provider = False

    lotus_idea_policy = Policy()
    assert lotus_idea_policy.allow_live_provider is False
""",
    ),
)


def write_lotus_ai_workflow_pack_fixture(tmp_path: Path) -> Path:
    lotus_ai_root = tmp_path / "lotus-ai"
    _write_fixture_files(lotus_ai_root, _BASE_WORKFLOW_PACK_FILES)
    return lotus_ai_root


def write_lotus_ai_workflow_pack_runtime_execution_fixture(tmp_path: Path) -> Path:
    lotus_ai_root = write_lotus_ai_workflow_pack_fixture(tmp_path)
    _write_fixture_files(lotus_ai_root, _RUNTIME_EXECUTION_WORKFLOW_PACK_FILES)
    return lotus_ai_root


def _write_fixture_files(lotus_ai_root: Path, files: tuple[tuple[str, str], ...]) -> None:
    for relative_path, content in files:
        _write(lotus_ai_root / relative_path, content)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.lstrip(), encoding="utf-8")
