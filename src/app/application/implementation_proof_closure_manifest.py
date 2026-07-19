from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from app.application.implementation_proof_artifact_registry import (
    IMPLEMENTATION_PROOF_ARTIFACT_SPECS,
    ProofArtifactClassificationStatus,
)
from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
)
from app.domain.proof_evidence import EvidenceClass

BLOCKER_CLOSURE_CONTRACT_PATH = Path(
    "contracts/implementation-proof/rfc0002-blocker-closure-manifest.v1.json"
)
SCHEMA_VERSION = "lotus-idea.rfc0002.blocker-closure-manifest.v1"
RFC_ID = "RFC-0002"
REPOSITORY = "lotus-idea"


def blocker_closure_manifest_errors(
    *,
    snapshot: ImplementationProofReadinessSnapshot,
    contract: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    _validate_contract_header(contract, errors)
    blocker_groups = _blocker_groups(contract, errors)
    blocker_to_group = _blocker_group_index(blocker_groups, errors)
    current_blockers = tuple(snapshot.overall_blockers)
    current_blocker_set = set(current_blockers)

    for blocker in current_blockers:
        if blocker not in blocker_to_group:
            errors.append(f"RFC-0002 blocker `{blocker}` has no closure-manifest owner")
    for blocker in blocker_to_group:
        if blocker not in current_blocker_set:
            errors.append(f"RFC-0002 blocker `{blocker}` is stale in the closure manifest")

    for group in blocker_groups:
        _validate_blocker_group(group, errors)
    _validate_proof_artifact_registry(errors)
    return errors


def blocker_closure_manifest_payload(
    *,
    snapshot: ImplementationProofReadinessSnapshot,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    blocker_to_group = _blocker_group_index(_blocker_groups(contract, []), [])
    capability_by_blocker = _capability_by_blocker(snapshot.capabilities)
    rows = []
    for blocker in snapshot.overall_blockers:
        group = blocker_to_group[blocker]
        capability = capability_by_blocker[blocker]
        rows.append(
            {
                "blocker": blocker,
                "capabilityId": capability.capability_id,
                "requiredEvidenceClass": group["requiredEvidenceClass"],
                "currentEvidenceClass": "none",
                "closureStatus": group["closureStatus"],
                "ownerIssue": group["ownerIssue"],
                "dependencyIssues": group.get("dependencyIssues", []),
                "sliceIds": group["sliceIds"],
                "currentEvidenceRefs": list(capability.evidence_refs),
                "supportedFeatureEffect": group["supportedFeatureEffect"],
            }
        )
    return {
        "schemaVersion": contract["schemaVersion"],
        "repository": snapshot.repository,
        "rfc": contract["rfc"],
        "trackingIssue": contract["trackingIssue"],
        "readinessStatus": snapshot.readiness_status,
        "supportabilityStatus": snapshot.supportability_status,
        "certificationReady": snapshot.certification_ready,
        "supportedFeaturesPromoted": snapshot.supported_features_promoted,
        "blockerCount": len(rows),
        "blockers": rows,
        "proofArtifactRegistry": [
            {
                "cliFlag": spec.cli_flag,
                "payloadArgument": spec.payload_argument,
                "refArgument": spec.ref_argument,
                "evidenceClass": spec.evidence_class,
                "effect": spec.effect,
                "trackingIssue": spec.tracking_issue,
                "status": spec.status,
            }
            for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS
        ],
    }


def _validate_contract_header(contract: Mapping[str, Any], errors: list[str]) -> None:
    expected = {
        "schemaVersion": SCHEMA_VERSION,
        "repository": REPOSITORY,
        "rfc": RFC_ID,
        "trackingIssue": "https://github.com/sgajbi/lotus-idea/issues/700",
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            errors.append(f"{BLOCKER_CLOSURE_CONTRACT_PATH}: `{key}` must be `{value}`")


def _blocker_groups(
    contract: Mapping[str, Any],
    errors: list[str],
) -> tuple[Mapping[str, Any], ...]:
    groups = contract.get("blockerGroups")
    if not isinstance(groups, list):
        errors.append(f"{BLOCKER_CLOSURE_CONTRACT_PATH}: `blockerGroups` must be a list")
        return ()
    return tuple(cast(Mapping[str, Any], group) for group in groups)


def _blocker_group_index(
    blocker_groups: Sequence[Mapping[str, Any]],
    errors: list[str],
) -> dict[str, Mapping[str, Any]]:
    blockers = [
        blocker for group in blocker_groups for blocker in _string_list(group.get("blockers"))
    ]
    counts = Counter(blockers)
    for blocker, count in counts.items():
        if count > 1:
            errors.append(f"RFC-0002 blocker `{blocker}` appears {count} times in the manifest")
    return {
        blocker: group
        for group in blocker_groups
        for blocker in _string_list(group.get("blockers"))
        if counts[blocker] == 1
    }


def _validate_blocker_group(group: Mapping[str, Any], errors: list[str]) -> None:
    group_id = _required_string(group, "groupId", errors)
    _required_string_list(group, "blockers", errors, group_id)
    _required_string_list(group, "sliceIds", errors, group_id)
    _validate_evidence_class(group, group_id, errors)
    _required_string(group, "closureStatus", errors, group_id)
    _required_string(group, "supportedFeatureEffect", errors, group_id)
    _validate_issue_ref(group.get("ownerIssue"), errors, group_id, required=True)
    dependency_issues = group.get("dependencyIssues", [])
    if not isinstance(dependency_issues, list):
        errors.append(f"{group_id}: `dependencyIssues` must be a list")
        return
    for issue in dependency_issues:
        _validate_issue_ref(issue, errors, group_id, required=False)


def _validate_evidence_class(
    group: Mapping[str, Any],
    group_id: str,
    errors: list[str],
) -> None:
    value = group.get("requiredEvidenceClass")
    try:
        EvidenceClass(cast(str, value))
    except ValueError:
        errors.append(f"{group_id}: `requiredEvidenceClass` must be a known evidence class")


def _validate_issue_ref(
    issue: object,
    errors: list[str],
    group_id: str,
    *,
    required: bool,
) -> None:
    if not isinstance(issue, Mapping):
        if required:
            errors.append(f"{group_id}: `ownerIssue` must be an issue reference object")
        return
    repository = issue.get("repository")
    number = issue.get("number")
    url = issue.get("url")
    if not isinstance(repository, str) or not repository.startswith("sgajbi/lotus-"):
        errors.append(f"{group_id}: issue repository must be an sgajbi Lotus repository")
    if not isinstance(number, int) or number <= 0:
        errors.append(f"{group_id}: issue number must be a positive integer")
    expected_url = f"https://github.com/{repository}/issues/{number}"
    if url != expected_url:
        errors.append(f"{group_id}: issue URL must be `{expected_url}`")


def _required_string(
    group: Mapping[str, Any],
    key: str,
    errors: list[str],
    group_id: str | None = None,
) -> str:
    value = group.get(key)
    if isinstance(value, str) and value:
        return value
    errors.append(f"{group_id or BLOCKER_CLOSURE_CONTRACT_PATH}: `{key}` must be a string")
    return "<invalid>"


def _required_string_list(
    group: Mapping[str, Any],
    key: str,
    errors: list[str],
    group_id: str,
) -> tuple[str, ...]:
    values = _string_list(group.get(key))
    if values:
        return values
    errors.append(f"{group_id}: `{key}` must contain at least one string")
    return ()


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item)


def _validate_proof_artifact_registry(errors: list[str]) -> None:
    for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS:
        if spec.status is not ProofArtifactClassificationStatus.CLASSIFIED:
            errors.append(f"{spec.cli_flag}: proof artifact must be classified before closure")
        if spec.evidence_class is None:
            errors.append(f"{spec.cli_flag}: proof artifact must declare an evidence class")
        if spec.tracking_issue <= 0:
            errors.append(f"{spec.cli_flag}: proof artifact must name a tracking issue")


def _capability_by_blocker(
    capabilities: Sequence[ImplementationProofCapabilityReadiness],
) -> dict[str, ImplementationProofCapabilityReadiness]:
    return {blocker: capability for capability in capabilities for blocker in capability.blockers}
