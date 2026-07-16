from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from app.application.runtime_evidence import sha256_json
from app.application.source_ingestion_scheduler import (
    scheduled_worker_source_contract_is_valid,
)
from tests.support.source_ingestion_scheduler_evidence import source_contract


ROOT = Path(__file__).resolve().parents[3]


def test_source_contract_is_closed_digest_bound_supporting_evidence() -> None:
    payload = source_contract(repository_root=ROOT)

    assert scheduled_worker_source_contract_is_valid(
        payload,
        repository_root=ROOT,
    )
    assert payload["evidenceClass"] == "source_contract"
    assert payload["blockerEffect"]["clears"] == []
    assert "scheduled_worker_deploy_proof_missing" in (
        payload["blockerEffect"]["preserves"]
    )
    assert payload["nonProofClaims"] == {
        "deploymentObserved": False,
        "scheduledExecutionObserved": False,
        "productionCertified": False,
    }
    assert payload["supportedFeaturePromoted"] is False
    assert payload["proofClosed"] is True


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("evidenceClass",), "deployment"),
        (("sourceContractValid",), False),
        (("blockerEffect", "clears"), ["scheduled_worker_deploy_proof_missing"]),
        (("nonProofClaims", "deploymentObserved"), True),
        (("nonProofClaims", "scheduledExecutionObserved"), True),
        (("nonProofClaims", "productionCertified"), True),
        (("supportedFeaturePromoted",), True),
    ),
)
def test_source_contract_rejects_class_or_claim_inflation(
    path: tuple[str, ...],
    value: object,
) -> None:
    payload = deepcopy(source_contract(repository_root=ROOT))
    _set(payload, path, value)
    _refresh_digest(payload)

    assert not scheduled_worker_source_contract_is_valid(payload)


def test_source_contract_rejects_unknown_fields() -> None:
    payload = source_contract(repository_root=ROOT)
    payload["deploymentSucceeded"] = True

    assert not scheduled_worker_source_contract_is_valid(payload)


def test_source_contract_rejects_source_file_digest_drift() -> None:
    payload = source_contract(repository_root=ROOT)
    payload["sourceFiles"][0]["sha256"] = f"sha256:{'0' * 64}"
    _refresh_digest(payload)

    assert not scheduled_worker_source_contract_is_valid(
        payload,
        repository_root=ROOT,
    )


def test_source_contract_rejects_scheduler_configuration_digest_drift() -> None:
    payload = source_contract(repository_root=ROOT)
    payload["schedulerConfigurationDigest"] = f"sha256:{'0' * 64}"
    _refresh_digest(payload)

    assert not scheduled_worker_source_contract_is_valid(payload)


def _set(payload: dict[str, object], path: tuple[str, ...], value: object) -> None:
    target = payload
    for part in path[:-1]:
        nested = target[part]
        assert isinstance(nested, dict)
        target = nested
    target[path[-1]] = value


def _refresh_digest(payload: dict[str, object]) -> None:
    material = {
        key: value
        for key, value in payload.items()
        if key != "sourceContractDigest"
    }
    payload["sourceContractDigest"] = sha256_json(material)
