from __future__ import annotations


REQUIRED_ADVISE_SOURCE_PRODUCT_EVIDENCE_PATHS = {
    "src/app/application/advise_source_product_evidence/__init__.py",
    "src/app/application/advise_source_product_evidence/contract.py",
    "src/app/application/advise_source_product_evidence/profiles.py",
    "src/app/application/implementation_proof_artifact_registry.py",
    "scripts/advise_source_product_evidence/__init__.py",
    "scripts/advise_source_product_evidence/generate_source_contract.py",
    "scripts/advise_source_product_evidence/source_contract_gate.py",
    "scripts/documentation/implementation_proof_artifact_registry.py",
    "tests/unit/advise_source_product_evidence/__init__.py",
    "tests/unit/advise_source_product_evidence/test_automation.py",
    "tests/unit/advise_source_product_evidence/test_contract.py",
    "tests/unit/implementation_proof/test_artifact_registry.py",
}

PROHIBITED_ADVISE_SOURCE_PRODUCT_EVIDENCE_PATHS = {
    "src/app/application/mandate_restriction_source_product_proof.py",
    "src/app/application/missing_risk_profile_source_product_proof.py",
    "scripts/generate_mandate_restriction_source_product_proof.py",
    "scripts/generate_missing_risk_profile_source_product_proof.py",
    "scripts/mandate_restriction_source_product_proof_contract_gate.py",
    "scripts/missing_risk_profile_source_product_proof_contract_gate.py",
    "tests/unit/test_mandate_restriction_source_product_proof.py",
    "tests/unit/test_missing_risk_profile_source_product_proof.py",
}
