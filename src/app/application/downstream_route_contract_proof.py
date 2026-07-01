from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any

from app.application.source_safe_cross_repo_proof import is_timezone_aware_datetime_text

_is_timezone_aware_datetime_text = is_timezone_aware_datetime_text

DOWNSTREAM_ROUTE_CONTRACT_PROOF_SCHEMA_VERSION = "lotus-idea.downstream-route-contract-proof.v1"

ADVISE_PROPOSAL_ROUTE_PROOF_ENV = "LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF"
MANAGE_ACTION_ROUTE_PROOF_ENV = "LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF"

ADVISE_ROUTE_BLOCKERS_CLEARED = ("advise_live_contract_proof_missing",)
MANAGE_ROUTE_BLOCKERS_CLEARED = ("manage_live_contract_proof_missing",)

ADVISE_PROPOSAL_ROUTE = "POST /advisory/proposals/idea-intake"
MANAGE_ACTION_ROUTE = "POST /api/v1/rebalance/idea-action-intake"

REMAINING_ADVISE_ROUTE_BLOCKERS = ("suitability_policy_authority_remains_lotus_advise",)
REMAINING_MANAGE_ROUTE_BLOCKERS = ("rebalance_execution_authority_remains_lotus_manage",)


@dataclass(frozen=True)
class DownstreamRouteContractProfile:
    proof_type: str
    proof_scope: str
    route_valid_field: str
    owner_repository: str
    source_authority: str
    downstream_authority: str
    contract_source_authority: str
    contract_authority_field: str | None
    approved_producer_product: str
    owned_product: str
    contract_path: str
    target_route: str
    blockers_cleared: tuple[str, ...]
    remaining_blockers: tuple[str, ...]
    proof_checks: tuple[str, ...]
    evidence_refs: tuple[str, ...]


ADVISE_PROPOSAL_ROUTE_PROFILE = DownstreamRouteContractProfile(
    proof_type="lotus_advise_idea_proposal_intake_route_contract",
    proof_scope="source_safe_advise_proposal_route_only",
    route_valid_field="adviseProposalRouteProofValid",
    owner_repository="lotus-advise",
    source_authority="lotus-idea",
    downstream_authority="lotus-advise",
    contract_source_authority="lotus-idea",
    contract_authority_field="proposal_authority",
    approved_producer_product="lotus-idea:IdeaCandidate:v1",
    owned_product="lotus-advise:AdvisoryProposalLifecycleRecord:v1",
    contract_path=("contracts/idea-proposal-intake/lotus-advise-idea-proposal-intake.v1.json"),
    target_route=ADVISE_PROPOSAL_ROUTE,
    blockers_cleared=ADVISE_ROUTE_BLOCKERS_CLEARED,
    remaining_blockers=REMAINING_ADVISE_ROUTE_BLOCKERS,
    proof_checks=(
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "downstreamContractProvesRoute",
        "downstreamContractPreservesNonProofBoundaries",
        "downstreamContractRetainsAuthorityBlockers",
    ),
    evidence_refs=(
        "../lotus-advise/contracts/idea-proposal-intake/lotus-advise-idea-proposal-intake.v1.json",
        "../lotus-advise/src/api/proposals/router.py",
        "../lotus-advise/src/core/proposals/service.py",
        "contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json",
        "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
        "RFC-0002-slice-12-advise-and-manage-conversion-realization.md",
        "GET /api/v1/downstream-realization/readiness",
        "GET /api/v1/implementation-proof/readiness",
    ),
)

MANAGE_ACTION_ROUTE_PROFILE = DownstreamRouteContractProfile(
    proof_type="lotus_manage_idea_action_intake_route_contract",
    proof_scope="source_safe_manage_action_route_only",
    route_valid_field="manageActionRouteProofValid",
    owner_repository="lotus-manage",
    source_authority="lotus-manage",
    downstream_authority="lotus-manage",
    contract_source_authority="lotus-manage",
    contract_authority_field=None,
    approved_producer_product="lotus-idea:IdeaCandidate:v1",
    owned_product="lotus-manage:PortfolioActionRegister:v1",
    contract_path=("contracts/idea-action-intake/lotus-manage-idea-action-intake.v1.json"),
    target_route=MANAGE_ACTION_ROUTE,
    blockers_cleared=MANAGE_ROUTE_BLOCKERS_CLEARED,
    remaining_blockers=REMAINING_MANAGE_ROUTE_BLOCKERS,
    proof_checks=(
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "downstreamContractProvesRoute",
        "downstreamContractPreservesNonProofBoundaries",
        "downstreamContractRetainsAuthorityBlockers",
    ),
    evidence_refs=(
        "../lotus-manage/contracts/idea-action-intake/lotus-manage-idea-action-intake.v1.json",
        "../lotus-manage/src/api/routers/rebalance_runs.py",
        "../lotus-manage/src/core/rebalance_runs/service.py",
        "contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json",
        "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
        "RFC-0002-slice-12-advise-and-manage-conversion-realization.md",
        "GET /api/v1/downstream-realization/readiness",
        "GET /api/v1/implementation-proof/readiness",
    ),
)


def build_advise_proposal_route_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    advise_root: Path | None = None,
) -> dict[str, Any]:
    return _build_route_contract_proof_payload(
        generated_at_utc=generated_at_utc,
        repository_root=repository_root,
        downstream_root=advise_root or repository_root.parent / "lotus-advise",
        profile=ADVISE_PROPOSAL_ROUTE_PROFILE,
    )


def build_manage_action_route_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    manage_root: Path | None = None,
) -> dict[str, Any]:
    return _build_route_contract_proof_payload(
        generated_at_utc=generated_at_utc,
        repository_root=repository_root,
        downstream_root=manage_root or repository_root.parent / "lotus-manage",
        profile=MANAGE_ACTION_ROUTE_PROFILE,
    )


def advise_proposal_route_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return _route_contract_proof_is_valid(
        payload,
        profile=ADVISE_PROPOSAL_ROUTE_PROFILE,
    )


def manage_action_route_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return _route_contract_proof_is_valid(
        payload,
        profile=MANAGE_ACTION_ROUTE_PROFILE,
    )


def load_advise_proposal_route_proof_from_env() -> tuple[dict[str, Any] | None, str | None]:
    return _load_route_contract_proof_from_env(ADVISE_PROPOSAL_ROUTE_PROOF_ENV)


def load_manage_action_route_proof_from_env() -> tuple[dict[str, Any] | None, str | None]:
    return _load_route_contract_proof_from_env(MANAGE_ACTION_ROUTE_PROOF_ENV)


def _build_route_contract_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    downstream_root: Path,
    profile: DownstreamRouteContractProfile,
) -> dict[str, Any]:
    contract = _optional_json(downstream_root / profile.contract_path)
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        downstream_root=downstream_root,
        owner_repository=profile.owner_repository,
        evidence_refs=profile.evidence_refs,
    )
    downstream_contract_proves_route = _downstream_contract_proves_route(contract, profile)
    downstream_contract_preserves_non_proof_boundaries = (
        _downstream_contract_preserves_non_proof_boundaries(contract)
    )
    downstream_contract_retains_authority_blockers = (
        _downstream_contract_retains_authority_blockers(contract, profile)
    )
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and downstream_contract_proves_route
        and downstream_contract_preserves_non_proof_boundaries
        and downstream_contract_retains_authority_blockers
    )
    return {
        "schemaVersion": DOWNSTREAM_ROUTE_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": profile.proof_type,
        "proofScope": profile.proof_scope,
        profile.route_valid_field: proof_valid,
        "aggregateBlockersCleared": profile.blockers_cleared,
        "evidenceRefs": profile.evidence_refs,
        "targetRoute": profile.target_route,
        "sourceAuthority": profile.source_authority,
        "downstreamAuthority": profile.downstream_authority,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "downstreamContractProvesRoute": downstream_contract_proves_route,
            "downstreamContractPreservesNonProofBoundaries": (
                downstream_contract_preserves_non_proof_boundaries
            ),
            "downstreamContractRetainsAuthorityBlockers": (
                downstream_contract_retains_authority_blockers
            ),
        },
        "remainingCertificationBlockers": profile.remaining_blockers,
        "downstreamExecutionProven": False,
        "suitabilityAuthorityGranted": False,
        "rebalanceExecutionAuthorityGranted": False,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def _route_contract_proof_is_valid(
    payload: Mapping[str, Any],
    *,
    profile: DownstreamRouteContractProfile,
) -> bool:
    if payload.get("schemaVersion") != DOWNSTREAM_ROUTE_CONTRACT_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != profile.proof_type:
        return False
    if payload.get("proofScope") != profile.proof_scope:
        return False
    if payload.get(profile.route_valid_field) is not True:
        return False
    if payload.get("targetRoute") != profile.target_route:
        return False
    if payload.get("sourceAuthority") != profile.source_authority:
        return False
    if payload.get("downstreamAuthority") != profile.downstream_authority:
        return False
    if payload.get("downstreamExecutionProven") is not False:
        return False
    if payload.get("suitabilityAuthorityGranted") is not False:
        return False
    if payload.get("rebalanceExecutionAuthorityGranted") is not False:
        return False
    if payload.get("clientPublicationAuthorityGranted") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != profile.blockers_cleared:
        return False
    if tuple(payload.get("evidenceRefs") or ()) != profile.evidence_refs:
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (profile.remaining_blockers):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return all(proof_checks.get(check_name) is True for check_name in profile.proof_checks)


def _load_route_contract_proof_from_env(
    env_name: str,
) -> tuple[dict[str, Any] | None, str | None]:
    path_value = os.getenv(env_name)
    if not path_value:
        return None, None
    path = Path(path_value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{env_name} must reference a JSON object")
    return payload, _source_safe_artifact_ref(path, env_name=env_name)


def _optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _source_safe_artifact_ref(path: Path, *, env_name: str) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return f"{env_name} artifact"


def _downstream_contract_proves_route(
    payload: dict[str, Any] | None,
    profile: DownstreamRouteContractProfile,
) -> bool:
    if payload is None:
        return False
    return (
        payload.get("repository") == profile.owner_repository
        and payload.get("approved_producer_repository") == "lotus-idea"
        and payload.get("approved_producer_product") == profile.approved_producer_product
        and payload.get("owned_product") == profile.owned_product
        and payload.get("source_authority") == profile.contract_source_authority
        and _contract_retains_downstream_authority(payload, profile)
        and payload.get("lifecycle_status") == "implemented"
        and payload.get("supportability_status") == "not_certified"
        and payload.get("route_existence_proven") is True
        and payload.get("downstream_execution_proven") is False
        and payload.get("supported_feature_promoted") is False
        and payload.get("target_route") == profile.target_route
    )


def _contract_retains_downstream_authority(
    payload: dict[str, Any],
    profile: DownstreamRouteContractProfile,
) -> bool:
    authority_field = profile.contract_authority_field
    if authority_field is None:
        return True
    return payload.get(authority_field) == profile.downstream_authority


def _downstream_contract_preserves_non_proof_boundaries(
    payload: dict[str, Any] | None,
) -> bool:
    if payload is None:
        return False
    boundaries = " ".join(str(boundary) for boundary in payload.get("non_proof_boundaries", ()))
    required_fragments = (
        "Proves only a live route foundation",
        "Does not grant suitability",
        "Does not create orders",
        "Does not promote a supported feature",
    )
    return all(fragment in boundaries for fragment in required_fragments)


def _downstream_contract_retains_authority_blockers(
    payload: dict[str, Any] | None,
    profile: DownstreamRouteContractProfile,
) -> bool:
    if payload is None:
        return False
    blockers = set(payload.get("certification_blockers", ()))
    return (
        not set(profile.blockers_cleared).intersection(blockers)
        and set(profile.remaining_blockers) <= blockers
    )


def _required_file_evidence_present(
    *,
    repository_root: Path,
    downstream_root: Path,
    owner_repository: str,
    evidence_refs: tuple[str, ...],
) -> bool:
    prefix = f"../{owner_repository}/"
    for ref in evidence_refs:
        if ref.startswith(("GET ", "POST ", "make ")):
            continue
        path = (
            downstream_root / ref.removeprefix(prefix)
            if ref.startswith(prefix)
            else repository_root / ref
        )
        if not path.is_file():
            return False
    return True
