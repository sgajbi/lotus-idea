from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, cast

from scripts.license_compliance_policy import (
    POLICY_PATH,
    ROOT,
    render_third_party_notice,
    validate_release_license_evidence,
    validate_license_policy,
)


def current_policy() -> dict[str, Any]:
    payload = json.loads((ROOT / POLICY_PATH).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def materialize_policy(tmp_path: Path, payload: dict[str, Any]) -> None:
    for lock_key in ("runtime_lock", "ci_lock"):
        contract = payload[lock_key]
        source = ROOT / contract["path"]
        target = tmp_path / contract["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    notice = tmp_path / payload["notice_path"]
    notice.write_text(render_third_party_notice(payload), encoding="utf-8")


def component(payload: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in payload["components"] if item["name"] == name)


def test_license_policy_accepts_current_locks_and_notice() -> None:
    assert validate_license_policy(current_policy()) == []


def test_license_policy_rejects_new_dependency_and_lock_hash_drift(tmp_path: Path) -> None:
    payload = current_policy()
    materialize_policy(tmp_path, payload)
    runtime_path = tmp_path / payload["runtime_lock"]["path"]
    runtime_path.write_text(
        runtime_path.read_text(encoding="utf-8") + "unreviewed-package==1.0.0\n",
        encoding="utf-8",
    )

    errors = validate_license_policy(payload, repository_root=tmp_path)

    assert "license policy runtime_lock hash does not match the resolved lock" in errors
    assert "license inventory missing locked component runtime:unreviewed-package" in errors


def test_license_policy_rejects_version_unknown_denied_and_conditional_drift(
    tmp_path: Path,
) -> None:
    payload = current_policy()
    component(payload, "anyio")["version"] = "0.0.0"
    component(payload, "ruff")["spdx"] = "LicenseRef-Unknown"
    component(payload, "pytest")["spdx"] = "AGPL-3.0-only"
    component(payload, "certifi")["obligations"] = []
    materialize_policy(tmp_path, payload)

    errors = validate_license_policy(payload, repository_root=tmp_path)

    assert "license inventory version drift for runtime:anyio" in errors
    assert "license LicenseRef-Unknown is not approved for ruff" in errors
    assert "license AGPL-3.0-only is not approved for pytest" in errors
    assert "conditional license obligations are required for certifi" in errors


def test_license_policy_accepts_active_exception_and_rejects_expired_exception(
    tmp_path: Path,
) -> None:
    payload = current_policy()
    component(payload, "ruff")["spdx"] = "GPL-3.0-only"
    payload["exceptions"] = [
        {
            "exception_id": "LIC-EX-001",
            "component": "ruff",
            "spdx": "GPL-3.0-only",
            "approved_by": ["legal", "security", "lotus-idea-owners"],
            "approval_evidence_ref": "https://github.com/sgajbi/lotus-idea/issues/999",
            "expires_on": "2026-07-31",
            "reason": "Bounded CI-only evaluation exception",
        }
    ]
    materialize_policy(tmp_path, payload)

    assert (
        validate_license_policy(
            payload,
            repository_root=tmp_path,
            as_of_date=date(2026, 7, 11),
        )
        == []
    )
    assert "license GPL-3.0-only is not approved for ruff" in validate_license_policy(
        payload,
        repository_root=tmp_path,
        as_of_date=date(2026, 8, 1),
    )
    assert "license exception LIC-EX-001 is expired" in validate_license_policy(
        payload,
        repository_root=tmp_path,
        as_of_date=date(2026, 8, 1),
    )


def test_license_policy_rejects_incomplete_approval_governance(tmp_path: Path) -> None:
    payload = current_policy()
    payload["approval"]["required_exception_approvals"] = ["lotus-idea-owners"]
    payload["approval"]["approval_evidence_required"] = False
    payload["approval"]["exception_expiry_required"] = False
    materialize_policy(tmp_path, payload)

    errors = validate_license_policy(payload, repository_root=tmp_path)

    assert "license exceptions must require app, security, and legal approval" in errors
    assert "license exceptions must require expiry" in errors
    assert "license approvals must require durable evidence" in errors


def test_license_policy_rejects_exception_without_all_approvals_or_evidence(
    tmp_path: Path,
) -> None:
    payload = current_policy()
    component(payload, "ruff")["spdx"] = "GPL-3.0-only"
    payload["exceptions"] = [
        {
            "exception_id": "LIC-EX-001",
            "component": "ruff",
            "spdx": "GPL-3.0-only",
            "approved_by": ["lotus-idea-owners"],
            "expires_on": "2026-07-31",
            "reason": "Bounded CI-only evaluation exception",
        }
    ]
    materialize_policy(tmp_path, payload)

    assert "license GPL-3.0-only is not approved for ruff" in validate_license_policy(
        payload,
        repository_root=tmp_path,
        as_of_date=date(2026, 7, 11),
    )

    payload["exceptions"][0]["approved_by"] = None
    assert "license GPL-3.0-only is not approved for ruff" in validate_license_policy(
        payload,
        repository_root=tmp_path,
        as_of_date=date(2026, 7, 11),
    )


def test_license_policy_rejects_orphaned_duplicate_or_malformed_exceptions(
    tmp_path: Path,
) -> None:
    payload = current_policy()
    payload["exceptions"] = [
        {
            "exception_id": "LIC-EX-001",
            "component": "missing-component",
            "spdx": "GPL-3.0-only",
            "approved_by": ["legal", "security", "lotus-idea-owners"],
            "approval_evidence_ref": "not-an-immutable-reference",
            "expires_on": "2026-07-31",
            "reason": "",
        },
        {
            "exception_id": "LIC-EX-001",
            "component": "ruff",
            "spdx": "GPL-3.0-only",
            "approved_by": ["legal", "security", "lotus-idea-owners"],
            "approval_evidence_ref": "https://github.com/sgajbi/lotus-idea/issues/999",
            "expires_on": "invalid",
            "reason": "Bounded evaluation",
        },
    ]
    materialize_policy(tmp_path, payload)

    errors = validate_license_policy(
        payload,
        repository_root=tmp_path,
        as_of_date=date(2026, 7, 11),
    )

    assert "license exception LIC-EX-001 component must be inventoried" in errors
    assert "license exception LIC-EX-001 requires immutable approval evidence" in errors
    assert "license exception LIC-EX-001 requires a bounded reason" in errors
    assert "duplicate license exception_id LIC-EX-001" in errors
    assert "license exception LIC-EX-001 requires an ISO expiry date" in errors


def test_license_policy_rejects_notice_external_and_asset_posture_drift(tmp_path: Path) -> None:
    payload = current_policy()
    materialize_policy(tmp_path, payload)
    (tmp_path / payload["notice_path"]).write_text("stale notice\n", encoding="utf-8")
    payload["external_components"] = []
    payload["asset_inventory"]["posture"] = "unreviewed_assets"

    errors = validate_license_policy(payload, repository_root=tmp_path)

    assert "third-party NOTICE must match deterministic policy output" in errors
    assert "license policy must classify governed base and scanner images" in errors
    assert "license policy must declare generated, model, and data asset posture" in errors


def test_lock_hashes_are_lowercase_sha256() -> None:
    payload = current_policy()
    for lock_key in ("runtime_lock", "ci_lock"):
        path = ROOT / payload[lock_key]["path"]
        assert payload[lock_key]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_release_license_evidence_binds_policy_notice_sbom_and_image() -> None:
    payload = current_policy()
    image = f"ghcr.io/sgajbi/lotus-idea@sha256:{'a' * 64}"
    sbom = {"serialNumber": "urn:uuid:sbom-001"}
    manifest: dict[str, Any] = {
        "container_image_digest_reference": image,
        "license_compliance": {
            "policy_contract": "contracts/compliance/lotus-idea-license-policy.v1.json",
            "policy_version": "1.0.0",
            "runtime_lock_sha256": payload["runtime_lock"]["sha256"],
            "ci_lock_sha256": payload["ci_lock"]["sha256"],
            "notice_path": "THIRD_PARTY_NOTICES.md",
            "notice_sha256": hashlib.sha256(
                (ROOT / "THIRD_PARTY_NOTICES.md").read_bytes()
            ).hexdigest(),
            "sbom_serial_number": "urn:uuid:sbom-001",
            "exception_ids": [],
            "target_artifact": image,
        },
    }

    assert validate_release_license_evidence(payload, manifest, sbom) == []
    manifest["license_compliance"]["target_artifact"] = "mutable:latest"
    manifest["license_compliance"]["sbom_serial_number"] = "different"

    errors = validate_release_license_evidence(payload, manifest, sbom)
    assert "release license evidence target_artifact must match policy/SBOM/artifact" in errors
    assert "release license evidence sbom_serial_number must match policy/SBOM/artifact" in errors
