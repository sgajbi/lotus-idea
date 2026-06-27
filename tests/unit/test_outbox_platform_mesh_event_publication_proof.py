from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application import outbox_platform_mesh_event_publication_proof as proof_module
from app.application.outbox_platform_mesh_event_publication_proof import (
    OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS_CLEARED,
    OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_SCHEMA_VERSION,
    REMAINING_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS,
    REQUIRED_OUTBOX_EVENT_TYPES,
    REQUIRED_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_EVIDENCE_REFS,
    REQUIRED_PLATFORM_PRODUCT_IDS,
    build_outbox_platform_mesh_event_publication_proof_payload,
    outbox_platform_mesh_event_publication_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_outbox_platform_mesh_event_publication_proof(
    tmp_path: Path,
) -> None:
    proof = _valid_outbox_platform_mesh_event_publication_proof(tmp_path)

    assert proof["schemaVersion"] == OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "outbox_platform_mesh_event_publication_contract"
    assert proof["proofScope"] == "bounded_source_safe_event_contract_and_platform_onboarding"
    assert proof["outboxPlatformMeshEventPublicationProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == (
        OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS_CLEARED
    )
    assert tuple(proof["evidenceRefs"]) == (
        REQUIRED_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_EVIDENCE_REFS
    )
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS
    )
    assert proof["eventTypeCount"] == len(REQUIRED_OUTBOX_EVENT_TYPES)
    assert proof["platformProductCount"] == len(REQUIRED_PLATFORM_PRODUCT_IDS)
    assert proof["externalBrokerPublicationSupported"] is False
    assert proof["downstreamConsumersCertified"] is False
    assert proof["gatewayWorkbenchProofPresent"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert outbox_platform_mesh_event_publication_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "idea_high_cash_001" not in serialized
    assert "eventId" not in serialized
    assert "aggregateId" not in serialized
    assert "idempotency" not in serialized


def test_rejects_outbox_platform_mesh_event_publication_proof_when_evidence_is_missing(
    tmp_path: Path,
) -> None:
    proof = build_outbox_platform_mesh_event_publication_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=tmp_path,
        platform_root=tmp_path / "missing-platform",
    )

    assert proof["outboxPlatformMeshEventPublicationProofValid"] is False
    assert outbox_platform_mesh_event_publication_proof_is_valid(proof) is False


def test_rejects_outbox_platform_mesh_event_publication_proof_with_naive_timestamp(
    tmp_path: Path,
) -> None:
    proof = build_outbox_platform_mesh_event_publication_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0),
        repository_root=ROOT,
        platform_root=_write_platform_fixture(tmp_path),
    )

    assert proof["outboxPlatformMeshEventPublicationProofValid"] is False
    assert outbox_platform_mesh_event_publication_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "outbox"),
        ("proofScope", "production_event_publication"),
        ("outboxPlatformMeshEventPublicationProofValid", False),
        ("externalBrokerPublicationSupported", True),
        ("downstreamConsumersCertified", True),
        ("gatewayWorkbenchProofPresent", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_outbox_platform_mesh_event_publication_proof_top_level_drift(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_outbox_platform_mesh_event_publication_proof(tmp_path)
    proof[field_name] = bad_value

    assert outbox_platform_mesh_event_publication_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", []),
        ("evidenceRefs", []),
        ("remainingCertificationBlockers", []),
        ("eventTypeCount", 0),
        ("platformProductCount", 0),
        ("proofChecks", []),
    ],
)
def test_rejects_outbox_platform_mesh_event_publication_proof_contract_drift(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_outbox_platform_mesh_event_publication_proof(tmp_path)
    proof[field_name] = bad_value

    assert outbox_platform_mesh_event_publication_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "makeTargetEvidencePresent",
        "eventContractSourceSafe",
        "eventFamilyCoveragePresent",
        "consumerContractLinksDeclaredEvents",
        "platformSourceManifestIncludesLotusIdea",
        "platformCatalogMapsIdeaProducts",
    ],
)
def test_rejects_outbox_platform_mesh_event_publication_proof_invalid_checks(
    check_name: str,
    tmp_path: Path,
) -> None:
    proof = _valid_outbox_platform_mesh_event_publication_proof(tmp_path)
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert outbox_platform_mesh_event_publication_proof_is_valid(proof) is False


def test_outbox_platform_mesh_event_publication_cli_writes_valid_artifact(
    tmp_path: Path,
) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "outbox-platform-mesh-event-publication-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-27T00:00:00Z",
            "--platform-root",
            str(_write_platform_fixture(tmp_path)),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert outbox_platform_mesh_event_publication_proof_is_valid(proof) is True


def test_outbox_platform_mesh_event_publication_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("event_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `event_id` is present"]


def test_outbox_platform_mesh_event_publication_rejects_non_object_payload(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "contract.json"
    contract_path.write_text("[]", encoding="utf-8")

    assert proof_module._load_json_object(contract_path) is None


def test_outbox_platform_mesh_event_publication_rejects_consumer_event_drift() -> None:
    event_contract = _valid_event_contract_payload()
    consumer_contract = _valid_consumer_contract_payload()
    consumer_contract["declaredConsumers"][0]["consumedEventTypes"] = ["unknown"]

    assert (
        proof_module._consumer_contract_links_declared_events(
            consumer_contract=consumer_contract,
            event_contract=event_contract,
        )
        is False
    )


def test_outbox_platform_mesh_event_publication_rejects_platform_catalog_drift() -> None:
    catalog = {
        "products": [
            {
                "product_id": REQUIRED_PLATFORM_PRODUCT_IDS[0],
                "producer_repository": "lotus-idea",
                "lifecycle_status": "active",
            }
        ]
    }

    assert proof_module._platform_catalog_maps_idea_products(catalog) is False


def _valid_outbox_platform_mesh_event_publication_proof(
    tmp_path: Path,
) -> dict[str, Any]:
    return build_outbox_platform_mesh_event_publication_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        platform_root=_write_platform_fixture(tmp_path),
    )


def _write_platform_fixture(tmp_path: Path) -> Path:
    platform_root = tmp_path / "lotus-platform"
    source_manifest_path = (
        platform_root
        / "platform-contracts/domain-data-products/domain-product-source-manifest.v1.json"
    )
    catalog_path = platform_root / "generated/domain-product-catalog.json"
    handoff_path = platform_root / "docs/operations/enterprise-mesh-completion-handoff.md"
    source_manifest_path.parent.mkdir(parents=True)
    catalog_path.parent.mkdir(parents=True)
    handoff_path.parent.mkdir(parents=True)
    source_manifest_path.write_text(
        json.dumps(
            {
                "repositories": [
                    {
                        "repository": "lotus-idea",
                        "source_mode": "repo_native",
                        "catalog_inclusion": "included",
                        "repo_native_status": "implemented",
                        "repo_native_declaration_path": "contracts/domain-data-products",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    catalog_path.write_text(
        json.dumps(
            {
                "products": [
                    {
                        "product_id": product_id,
                        "producer_repository": "lotus-idea",
                        "lifecycle_status": "proposed",
                    }
                    for product_id in REQUIRED_PLATFORM_PRODUCT_IDS
                ]
            }
        ),
        encoding="utf-8",
    )
    handoff_path.write_text("lotus-idea future-wave event publication proof\n", encoding="utf-8")
    return platform_root


def _valid_event_contract_payload() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(
            (ROOT / "contracts/outbox-events/lotus-idea-outbox-events.v1.json").read_text(
                encoding="utf-8"
            )
        ),
    )


def _valid_consumer_contract_payload() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(
            (ROOT / "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json").read_text(
                encoding="utf-8"
            )
        ),
    )


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_outbox_platform_mesh_event_publication_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_outbox_platform_mesh_event_publication_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "outbox_platform_mesh_event_publication_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "outbox_platform_mesh_event_publication_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
