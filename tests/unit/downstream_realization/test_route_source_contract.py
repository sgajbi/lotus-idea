from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from app.application.downstream_realization.route_source_contract import (
    ADVISE_PROPOSAL_ROUTE,
    ADVISE_ROUTE_PROFILE,
    ADVISE_ROUTE_SOURCE_CONTRACT_ENV,
    MANAGE_ACTION_ROUTE,
    MANAGE_ROUTE_PROFILE,
    MANAGE_ROUTE_SOURCE_CONTRACT_ENV,
    REQUIRED_ADVISE_PRODUCER_CERTIFICATION_BLOCKERS,
    REQUIRED_MANAGE_PRODUCER_CERTIFICATION_BLOCKERS,
    ROUTE_SOURCE_CONTRACT_SCHEMA_VERSION,
    advise_route_source_contract_is_valid,
    build_advise_route_source_contract_payload,
    build_manage_route_source_contract_payload,
    load_advise_route_source_contract_from_env,
    load_manage_route_source_contract_from_env,
    manage_route_source_contract_is_valid,
)
from app.domain.proof_evidence import EvidenceClass


ROOT = Path(__file__).resolve().parents[3]
GENERATED_AT = datetime(2026, 7, 15, 0, 0, tzinfo=UTC)


@pytest.mark.parametrize("family", ["advise", "manage"])
def test_builds_digest_bound_source_contract_without_clearing_live_blockers(
    tmp_path: Path, family: str
) -> None:
    payload = _valid_payload(tmp_path, family)
    profile = ADVISE_ROUTE_PROFILE if family == "advise" else MANAGE_ROUTE_PROFILE
    validator = (
        advise_route_source_contract_is_valid
        if family == "advise"
        else manage_route_source_contract_is_valid
    )

    assert payload["schemaVersion"] == ROUTE_SOURCE_CONTRACT_SCHEMA_VERSION
    assert payload["evidenceClass"] == EvidenceClass.SOURCE_CONTRACT.value
    assert payload["sourceContractValid"] is True
    assert payload["sourceContractBlockersSatisfied"] == ()
    remaining_blockers = cast(tuple[str, ...], payload["remainingCertificationBlockers"])
    source_authority = _source_authority(payload)
    assert remaining_blockers == profile.remaining_blockers
    assert payload["runtimeExecutionObserved"] is False
    assert payload["downstreamRecordAccepted"] is False
    assert all(item["repository"] == profile.owner_repository for item in source_authority)
    assert all(len(cast(str, item["sha256"])) == 64 for item in source_authority)
    assert validator(payload) is True


def test_missing_sibling_sources_fail_closed(tmp_path: Path) -> None:
    advise = build_advise_route_source_contract_payload(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        advise_root=tmp_path / "missing-advise",
    )
    manage = build_manage_route_source_contract_payload(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        manage_root=tmp_path / "missing-manage",
    )

    assert advise["sourceContractValid"] is False
    assert manage["sourceContractValid"] is False
    assert advise_route_source_contract_is_valid(advise) is False
    assert manage_route_source_contract_is_valid(manage) is False


def test_source_mutation_changes_bound_digest(tmp_path: Path) -> None:
    downstream_root = _write_fixture(tmp_path, "advise")
    before = build_advise_route_source_contract_payload(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        advise_root=downstream_root,
    )
    route_path = downstream_root / ADVISE_ROUTE_PROFILE.source_refs[1]
    route_path.write_text("# changed route declaration\n", encoding="utf-8")

    after = build_advise_route_source_contract_payload(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        advise_root=downstream_root,
    )

    assert before["sourceAuthority"][1]["sha256"] != after["sourceAuthority"][1]["sha256"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evidenceClass", EvidenceClass.RUNTIME_EXECUTION.value),
        ("generatedAtUtc", "2026-07-15T00:00:00"),
        ("sourceContractBlockersSatisfied", ["advise_live_contract_proof_missing"]),
        ("routeServingObserved", True),
        ("requestAuthorizationObserved", True),
        ("tenantIsolationObserved", True),
        ("runtimeExecutionObserved", True),
        ("downstreamRecordAccepted", True),
        ("suitabilityAuthorityGranted", True),
        ("rebalanceExecutionAuthorityGranted", True),
        ("productionCertificationGranted", True),
        ("supportedFeaturePromoted", True),
        ("certificationClosed", True),
    ],
)
def test_validator_rejects_evidence_and_authority_claim_inflation(
    tmp_path: Path, field: str, value: object
) -> None:
    payload = _valid_payload(tmp_path, "advise")
    payload[field] = value

    assert advise_route_source_contract_is_valid(payload) is False


def test_validator_rejects_unknown_fields_and_source_authority_substitution(
    tmp_path: Path,
) -> None:
    payload = _valid_payload(tmp_path, "manage")
    payload["runtimeCertified"] = True
    assert manage_route_source_contract_is_valid(payload) is False

    payload = _valid_payload(tmp_path, "manage")
    _source_authority(payload)[0]["repository"] = "lotus-idea"
    assert manage_route_source_contract_is_valid(payload) is False

    payload = _valid_payload(tmp_path, "manage")
    _source_authority(payload)[0]["sha256"] = "not-a-digest"
    assert manage_route_source_contract_is_valid(payload) is False


def test_validator_rejects_malformed_source_authority_collection(tmp_path: Path) -> None:
    payload = _valid_payload(tmp_path, "manage")
    payload["sourceAuthority"] = ()
    assert manage_route_source_contract_is_valid(payload) is False

    payload = _valid_payload(tmp_path, "manage")
    source_authority = list(_source_authority(payload))
    source_authority[0] = {"repository": "lotus-manage"}
    payload["sourceAuthority"] = source_authority
    assert manage_route_source_contract_is_valid(payload) is False


@pytest.mark.parametrize("family", ["advise", "manage"])
def test_contract_requires_every_producer_owned_certification_blocker(
    tmp_path: Path, family: str
) -> None:
    profile = ADVISE_ROUTE_PROFILE if family == "advise" else MANAGE_ROUTE_PROFILE
    root = _write_fixture(tmp_path, family)
    contract_path = root / profile.contract_path
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["certification_blockers"].remove(profile.required_producer_certification_blockers[0])
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    payload = _build_payload(root, family)

    assert payload["sourceContractValid"] is False
    validator = (
        advise_route_source_contract_is_valid
        if family == "advise"
        else manage_route_source_contract_is_valid
    )
    assert validator(payload) is False


@pytest.mark.parametrize(
    "field",
    ["runtime_intake_receipt_proven", "receipt_outcomes", "principal_capability"],
)
def test_advise_contract_requires_current_intake_receipt_boundary(
    tmp_path: Path, field: str
) -> None:
    root = _write_fixture(tmp_path, "advise")
    contract_path = root / ADVISE_ROUTE_PROFILE.contract_path
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract.pop(field)
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    payload = build_advise_route_source_contract_payload(
        generated_at_utc=GENERATED_AT, repository_root=ROOT, advise_root=root
    )

    assert payload["sourceContractValid"] is False
    assert advise_route_source_contract_is_valid(payload) is False


@pytest.mark.parametrize("family", ["advise", "manage"])
def test_contract_allows_additional_producer_certification_blockers(
    tmp_path: Path, family: str
) -> None:
    profile = ADVISE_ROUTE_PROFILE if family == "advise" else MANAGE_ROUTE_PROFILE
    root = _write_fixture(tmp_path, family)
    contract_path = root / profile.contract_path
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["certification_blockers"].append("future_producer_owned_blocker")
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    assert _build_payload(root, family)["sourceContractValid"] is True


@pytest.mark.parametrize("family", ["advise", "manage"])
def test_contract_rejects_consumer_readiness_blockers_as_producer_certification(
    tmp_path: Path, family: str
) -> None:
    profile = ADVISE_ROUTE_PROFILE if family == "advise" else MANAGE_ROUTE_PROFILE
    root = _write_fixture(tmp_path, family)
    contract_path = root / profile.contract_path
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["certification_blockers"] = list(profile.remaining_blockers)
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    assert _build_payload(root, family)["sourceContractValid"] is False


@pytest.mark.parametrize(
    ("loader", "env_name"),
    [
        (load_advise_route_source_contract_from_env, ADVISE_ROUTE_SOURCE_CONTRACT_ENV),
        (load_manage_route_source_contract_from_env, MANAGE_ROUTE_SOURCE_CONTRACT_ENV),
    ],
)
def test_environment_loader_is_optional_and_requires_an_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, loader: object, env_name: str
) -> None:
    monkeypatch.delenv(env_name, raising=False)
    assert loader() == (None, None)  # type: ignore[operator]

    artifact = tmp_path / "proof.json"
    artifact.write_text("[]", encoding="utf-8")
    monkeypatch.setenv(env_name, str(artifact))
    with pytest.raises(ValueError, match="must reference a JSON object"):
        loader()  # type: ignore[operator]


def test_environment_loader_reports_relative_and_external_artifact_refs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "proof.json"
    artifact.write_text('{"schemaVersion": "test"}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(ADVISE_ROUTE_SOURCE_CONTRACT_ENV, artifact.name)

    payload, artifact_ref = load_advise_route_source_contract_from_env()

    assert payload == {"schemaVersion": "test"}
    assert artifact_ref == "proof.json"

    monkeypatch.chdir(ROOT)
    monkeypatch.setenv(MANAGE_ROUTE_SOURCE_CONTRACT_ENV, str(artifact))
    payload, artifact_ref = load_manage_route_source_contract_from_env()

    assert payload == {"schemaVersion": "test"}
    assert artifact_ref == f"{MANAGE_ROUTE_SOURCE_CONTRACT_ENV} artifact"


def test_contract_gate_passes_closed_source_contracts() -> None:
    module = _load_script("route_source_contract_gate")

    assert module.validate_route_source_contracts() == []


@pytest.mark.parametrize(
    ("script_name", "root_arg"),
    [
        ("generate_advise_route_source_contract", "--advise-root"),
        ("generate_manage_route_source_contract", "--manage-root"),
    ],
)
def test_generators_allow_missing_sibling_evidence_without_hiding_drift(
    tmp_path: Path, script_name: str, root_arg: str
) -> None:
    module = _load_script(script_name)
    output = tmp_path / "proof.json"

    assert (
        module.main(
            [
                "--generated-at-utc",
                GENERATED_AT.isoformat(),
                root_arg,
                str(tmp_path / "missing-owner"),
                "--output",
                str(output),
                "--allow-missing-evidence",
            ]
        )
        == 0
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["sourceContractValid"] is False
    assert any(item["sha256"] is None for item in payload["sourceAuthority"])


def test_manage_generator_fails_present_contract_drift_even_when_missing_is_allowed(
    tmp_path: Path,
) -> None:
    module = _load_script("generate_manage_route_source_contract")
    manage_root = _write_fixture(tmp_path, "manage")
    contract_path = manage_root / MANAGE_ROUTE_PROFILE.contract_path
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["non_proof_boundaries"] = ["unsupported boundary"]
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    assert (
        module.main(
            [
                "--generated-at-utc",
                GENERATED_AT.isoformat(),
                "--manage-root",
                str(manage_root),
                "--output",
                str(tmp_path / "proof.json"),
                "--allow-missing-evidence",
            ]
        )
        == 1
    )


def _valid_payload(tmp_path: Path, family: str) -> dict[str, object]:
    root = _write_fixture(tmp_path, family)
    return _build_payload(root, family)


def _build_payload(root: Path, family: str) -> dict[str, object]:
    if family == "advise":
        return build_advise_route_source_contract_payload(
            generated_at_utc=GENERATED_AT, repository_root=ROOT, advise_root=root
        )
    return build_manage_route_source_contract_payload(
        generated_at_utc=GENERATED_AT, repository_root=ROOT, manage_root=root
    )


def _source_authority(payload: dict[str, object]) -> tuple[dict[str, object], ...]:
    value = payload["sourceAuthority"]
    assert isinstance(value, (list, tuple))
    assert all(isinstance(item, dict) for item in value)
    return tuple(cast(dict[str, object], item) for item in value)


def _write_fixture(tmp_path: Path, family: str) -> Path:
    profile = ADVISE_ROUTE_PROFILE if family == "advise" else MANAGE_ROUTE_PROFILE
    root = tmp_path / profile.owner_repository
    for ref in profile.source_refs:
        path = root / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# source declaration\n", encoding="utf-8")
    contract = _contract_payload(family)
    (root / profile.contract_path).write_text(json.dumps(contract), encoding="utf-8")
    return root


def _contract_payload(family: str) -> dict[str, object]:
    advise = family == "advise"
    profile = ADVISE_ROUTE_PROFILE if advise else MANAGE_ROUTE_PROFILE
    payload: dict[str, object] = {
        "repository": profile.owner_repository,
        "approved_producer_repository": "lotus-idea",
        "approved_producer_product": profile.approved_producer_product,
        "owned_product": profile.owned_product,
        "source_authority": profile.contract_source_authority,
        "lifecycle_status": "implemented",
        "supportability_status": "not_certified",
        "route_existence_proven": True,
        "runtime_intake_receipt_proven": advise,
        "downstream_execution_proven": False,
        "supported_feature_promoted": False,
        "target_route": ADVISE_PROPOSAL_ROUTE if advise else MANAGE_ACTION_ROUTE,
        "non_proof_boundaries": [
            "Proves only a live route foundation from static declarations.",
            "Does not grant suitability, policy, mandate, or client authority.",
            "Does not create orders, fills, or settlement records.",
            "Does not promote a supported feature.",
        ],
        "certification_blockers": list(
            REQUIRED_ADVISE_PRODUCER_CERTIFICATION_BLOCKERS
            if advise
            else REQUIRED_MANAGE_PRODUCER_CERTIFICATION_BLOCKERS
        ),
    }
    if advise:
        payload["proposal_authority"] = "lotus-advise"
        payload["receipt_outcomes"] = ["ACCEPTED", "ACCEPTED_REPLAYED", "REJECTED"]
        payload["principal_capability"] = "advisory.idea_proposal_intake.accept"
        payload["local_dev_principal_source"] = "trusted_headers_until_production_idp_available"
        payload["non_proof_boundaries"] = [
            "Proves a live executable intake receipt for lotus-idea conversion-intent handoff "
            "into lotus-advise, including accepted, replayed, rejected, and "
            "idempotency-conflict behavior.",
            "Does not grant suitability, recommendation, approval, consent, execution, order, "
            "OMS, fill, settlement, or client-communication authority.",
            "Does not create orders, advisory proposal lifecycle records, suitability "
            "decisions, approvals, execution instructions, fills, settlement records, or "
            "client messages.",
            "Does not promote a supported feature, client-ready workflow, data-product "
            "certification, or downstream execution proof.",
        ]
    return payload


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / "downstream_realization" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
