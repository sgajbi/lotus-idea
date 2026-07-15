from pathlib import Path


PRODUCER_SOURCE_FILES = {
    "src/app/contracts/workflow_run_attestation.py": (
        "class WorkflowRunAttestationClaims:\n"
        "    model_risk_approval_ref = None\n"
        "    replay_nonce = None\n"
    ),
    "src/app/services/workflow_run_attestation_signing.py": (
        "EdDSA = 'EdDSA'\nsignature_base64url = ''\ncanonical_attestation_payload = b''\n"
    ),
    "src/app/services/workflow_run_attestation_issuance.py": (
        "model_risk_status = 'approved'\napproval_ref = 'fixture'\nstubbed = False\n"
    ),
    "src/app/routers/workflow_run_attestations.py": "# Contract fixture.\n",
    "tests/unit/test_workflow_run_attestation_signing.py": "# Contract fixture.\n",
    "tests/unit/test_workflow_run_attestation_issuance.py": "# Contract fixture.\n",
    "tests/integration/test_workflow_run_attestation_api_contract.py": "# Contract fixture.\n",
}


def write_lotus_ai_attestation_source(root: Path) -> Path:
    for relative_path, content in PRODUCER_SOURCE_FILES.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root
