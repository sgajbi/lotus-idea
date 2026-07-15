from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any

from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.source_authority import (
    SourceAuthoritySource,
    build_source_authority_records,
    source_authority_records_are_valid,
)
from app.application.source_safe_cross_repo_proof import is_timezone_aware_datetime_text
from app.domain.proof_evidence import EvidenceClass


ROUTE_SOURCE_CONTRACT_SCHEMA_VERSION = "lotus-idea.downstream-route-source-contract.v2"
ADVISE_ROUTE_SOURCE_CONTRACT_ENV = "LOTUS_IDEA_ADVISE_ROUTE_SOURCE_CONTRACT_PROOF"
MANAGE_ROUTE_SOURCE_CONTRACT_ENV = "LOTUS_IDEA_MANAGE_ROUTE_SOURCE_CONTRACT_PROOF"

ADVISE_PROPOSAL_ROUTE = "POST /advisory/proposals/idea-intake"
MANAGE_ACTION_ROUTE = "POST /api/v1/rebalance/idea-action-intake"

ROUTE_SOURCE_CONTRACT_BLOCKERS_SATISFIED: tuple[str, ...] = ()
REMAINING_ADVISE_ROUTE_BLOCKERS = (
    "advise_live_contract_proof_missing",
    "suitability_policy_authority_remains_lotus_advise",
)
REMAINING_MANAGE_ROUTE_BLOCKERS = (
    "manage_live_contract_proof_missing",
    "rebalance_execution_authority_remains_lotus_manage",
)

_CONTRACT_CHECK_FIELDS = frozenset(
    {
        "timezoneAwareGeneratedAtUtc",
        "sourceAuthorityDigestBound",
        "downstreamContractDeclaresRoute",
        "downstreamContractPreservesBoundaries",
        "downstreamContractRetainsBlockers",
    }
)
_PAYLOAD_FIELDS = frozenset(
    {
        "schemaVersion",
        "repository",
        "generatedAtUtc",
        "proofType",
        "proofScope",
        "evidenceClass",
        "sourceContractValid",
        "sourceContractBlockersSatisfied",
        "evidenceRefs",
        "sourceAuthority",
        "sourceRepository",
        "downstreamAuthority",
        "targetRoute",
        "contractChecks",
        "remainingCertificationBlockers",
        "routeServingObserved",
        "requestAuthorizationObserved",
        "tenantIsolationObserved",
        "runtimeExecutionObserved",
        "downstreamRecordAccepted",
        "suitabilityAuthorityGranted",
        "rebalanceExecutionAuthorityGranted",
        "clientPublicationAuthorityGranted",
        "productionCertificationGranted",
        "supportedFeaturePromoted",
        "certificationClosed",
    }
)


@dataclass(frozen=True)
class RouteSourceContractProfile:
    proof_type: str
    proof_scope: str
    owner_repository: str
    source_repository: str
    downstream_authority: str
    contract_source_authority: str
    contract_authority_field: str | None
    approved_producer_product: str
    owned_product: str
    contract_path: str
    target_route: str
    remaining_blockers: tuple[str, ...]
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]


ADVISE_ROUTE_PROFILE = RouteSourceContractProfile(
    proof_type="lotus_advise_idea_proposal_intake_route_source_contract",
    proof_scope="advise_route_declaration_and_contract_compatibility",
    owner_repository="lotus-advise",
    source_repository="lotus-idea",
    downstream_authority="lotus-advise",
    contract_source_authority="lotus-idea",
    contract_authority_field="proposal_authority",
    approved_producer_product="lotus-idea:IdeaCandidate:v1",
    owned_product="lotus-advise:AdvisoryProposalLifecycleRecord:v1",
    contract_path="contracts/idea-proposal-intake/lotus-advise-idea-proposal-intake.v1.json",
    target_route=ADVISE_PROPOSAL_ROUTE,
    remaining_blockers=REMAINING_ADVISE_ROUTE_BLOCKERS,
    source_refs=(
        "contracts/idea-proposal-intake/lotus-advise-idea-proposal-intake.v1.json",
        "src/api/proposals/router.py",
        "src/core/proposals/service.py",
    ),
    evidence_refs=(
        "../lotus-advise/contracts/idea-proposal-intake/lotus-advise-idea-proposal-intake.v1.json",
        "../lotus-advise/src/api/proposals/router.py",
        "../lotus-advise/src/core/proposals/service.py",
        "src/app/application/downstream_realization/route_source_contract.py",
        "scripts/downstream_realization/route_source_contract_gate.py",
        "contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json",
        "GET /api/v1/downstream-realization/readiness",
        "GET /api/v1/implementation-proof/readiness",
    ),
)

MANAGE_ROUTE_PROFILE = RouteSourceContractProfile(
    proof_type="lotus_manage_idea_action_intake_route_source_contract",
    proof_scope="manage_route_declaration_and_contract_compatibility",
    owner_repository="lotus-manage",
    source_repository="lotus-manage",
    downstream_authority="lotus-manage",
    contract_source_authority="lotus-manage",
    contract_authority_field=None,
    approved_producer_product="lotus-idea:IdeaCandidate:v1",
    owned_product="lotus-manage:PortfolioActionRegister:v1",
    contract_path="contracts/idea-action-intake/lotus-manage-idea-action-intake.v1.json",
    target_route=MANAGE_ACTION_ROUTE,
    remaining_blockers=REMAINING_MANAGE_ROUTE_BLOCKERS,
    source_refs=(
        "contracts/idea-action-intake/lotus-manage-idea-action-intake.v1.json",
        "src/api/routers/rebalance_runs.py",
        "src/core/rebalance_runs/service.py",
    ),
    evidence_refs=(
        "../lotus-manage/contracts/idea-action-intake/lotus-manage-idea-action-intake.v1.json",
        "../lotus-manage/src/api/routers/rebalance_runs.py",
        "../lotus-manage/src/core/rebalance_runs/service.py",
        "src/app/application/downstream_realization/route_source_contract.py",
        "scripts/downstream_realization/route_source_contract_gate.py",
        "contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json",
        "GET /api/v1/downstream-realization/readiness",
        "GET /api/v1/implementation-proof/readiness",
    ),
)


def build_advise_route_source_contract_payload(
    *, generated_at_utc: datetime, repository_root: Path, advise_root: Path | None = None
) -> dict[str, Any]:
    return _build_route_source_contract(
        generated_at_utc=generated_at_utc,
        downstream_root=advise_root or repository_root.parent / "lotus-advise",
        profile=ADVISE_ROUTE_PROFILE,
    )


def build_manage_route_source_contract_payload(
    *, generated_at_utc: datetime, repository_root: Path, manage_root: Path | None = None
) -> dict[str, Any]:
    return _build_route_source_contract(
        generated_at_utc=generated_at_utc,
        downstream_root=manage_root or repository_root.parent / "lotus-manage",
        profile=MANAGE_ROUTE_PROFILE,
    )


def advise_route_source_contract_is_valid(payload: Mapping[str, Any]) -> bool:
    return _route_source_contract_is_valid(payload, profile=ADVISE_ROUTE_PROFILE)


def manage_route_source_contract_is_valid(payload: Mapping[str, Any]) -> bool:
    return _route_source_contract_is_valid(payload, profile=MANAGE_ROUTE_PROFILE)


def load_advise_route_source_contract_from_env() -> tuple[dict[str, Any] | None, str | None]:
    return _load_from_env(ADVISE_ROUTE_SOURCE_CONTRACT_ENV)


def load_manage_route_source_contract_from_env() -> tuple[dict[str, Any] | None, str | None]:
    return _load_from_env(MANAGE_ROUTE_SOURCE_CONTRACT_ENV)


def _build_route_source_contract(
    *, generated_at_utc: datetime, downstream_root: Path, profile: RouteSourceContractProfile
) -> dict[str, Any]:
    contract = _optional_json(downstream_root / profile.contract_path)
    timezone_aware = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    source_authority = _source_authority(downstream_root, profile)
    digests_bound = all(isinstance(item["sha256"], str) for item in source_authority)
    declares_route = _contract_declares_route(contract, profile)
    preserves_boundaries = _contract_preserves_boundaries(contract)
    retains_blockers = _contract_retains_blockers(contract, profile)
    valid = (
        timezone_aware
        and digests_bound
        and declares_route
        and preserves_boundaries
        and retains_blockers
    )
    return {
        "schemaVersion": ROUTE_SOURCE_CONTRACT_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": profile.proof_type,
        "proofScope": profile.proof_scope,
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "sourceContractValid": valid,
        "sourceContractBlockersSatisfied": ROUTE_SOURCE_CONTRACT_BLOCKERS_SATISFIED,
        "evidenceRefs": profile.evidence_refs,
        "sourceAuthority": source_authority,
        "sourceRepository": profile.source_repository,
        "downstreamAuthority": profile.downstream_authority,
        "targetRoute": profile.target_route,
        "contractChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware,
            "sourceAuthorityDigestBound": digests_bound,
            "downstreamContractDeclaresRoute": declares_route,
            "downstreamContractPreservesBoundaries": preserves_boundaries,
            "downstreamContractRetainsBlockers": retains_blockers,
        },
        "remainingCertificationBlockers": profile.remaining_blockers,
        "routeServingObserved": False,
        "requestAuthorizationObserved": False,
        "tenantIsolationObserved": False,
        "runtimeExecutionObserved": False,
        "downstreamRecordAccepted": False,
        "suitabilityAuthorityGranted": False,
        "rebalanceExecutionAuthorityGranted": False,
        "clientPublicationAuthorityGranted": False,
        "productionCertificationGranted": False,
        "supportedFeaturePromoted": False,
        "certificationClosed": False,
    }


def _route_source_contract_is_valid(
    payload: Mapping[str, Any], *, profile: RouteSourceContractProfile
) -> bool:
    if set(payload) not in (_PAYLOAD_FIELDS, _PAYLOAD_FIELDS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    expected = {
        "schemaVersion": ROUTE_SOURCE_CONTRACT_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofType": profile.proof_type,
        "proofScope": profile.proof_scope,
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "sourceContractValid": True,
        "sourceContractBlockersSatisfied": ROUTE_SOURCE_CONTRACT_BLOCKERS_SATISFIED,
        "evidenceRefs": profile.evidence_refs,
        "sourceRepository": profile.source_repository,
        "downstreamAuthority": profile.downstream_authority,
        "targetRoute": profile.target_route,
        "remainingCertificationBlockers": profile.remaining_blockers,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        return False
    if any(
        payload.get(field) is not False
        for field in _PAYLOAD_FIELDS
        if field.endswith("Observed")
        or field.endswith("Accepted")
        or field.endswith("Granted")
        or field in {"supportedFeaturePromoted", "certificationClosed"}
    ):
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if not _source_authority_is_valid(payload.get("sourceAuthority"), profile):
        return False
    checks = payload.get("contractChecks")
    return (
        isinstance(checks, Mapping)
        and set(checks) == _CONTRACT_CHECK_FIELDS
        and all(checks.get(name) is True for name in _CONTRACT_CHECK_FIELDS)
    )


def _source_authority(
    downstream_root: Path, profile: RouteSourceContractProfile
) -> tuple[dict[str, str | None], ...]:
    return build_source_authority_records(_source_authority_sources(downstream_root, profile))


def _source_authority_is_valid(value: object, profile: RouteSourceContractProfile) -> bool:
    return source_authority_records_are_valid(
        value,
        expected_sources=_source_authority_sources(Path(), profile),
    )


def _source_authority_sources(
    downstream_root: Path,
    profile: RouteSourceContractProfile,
) -> tuple[SourceAuthoritySource, ...]:
    prefix = f"../{profile.owner_repository}/"
    return tuple(
        SourceAuthoritySource(
            profile.owner_repository,
            f"{prefix}{ref}",
            downstream_root / ref,
        )
        for ref in profile.source_refs
    )


def _contract_declares_route(
    payload: dict[str, Any] | None, profile: RouteSourceContractProfile
) -> bool:
    return bool(
        payload
        and payload.get("repository") == profile.owner_repository
        and payload.get("approved_producer_repository") == "lotus-idea"
        and payload.get("approved_producer_product") == profile.approved_producer_product
        and payload.get("owned_product") == profile.owned_product
        and payload.get("source_authority") == profile.contract_source_authority
        and _contract_retains_authority(payload, profile)
        and payload.get("lifecycle_status") == "implemented"
        and payload.get("supportability_status") == "not_certified"
        and payload.get("route_existence_proven") is True
        and payload.get("downstream_execution_proven") is False
        and payload.get("supported_feature_promoted") is False
        and payload.get("target_route") == profile.target_route
    )


def _contract_retains_authority(
    payload: dict[str, Any], profile: RouteSourceContractProfile
) -> bool:
    return (
        profile.contract_authority_field is None
        or payload.get(profile.contract_authority_field) == profile.downstream_authority
    )


def _contract_preserves_boundaries(payload: dict[str, Any] | None) -> bool:
    boundaries = " ".join(str(value) for value in (payload or {}).get("non_proof_boundaries", ()))
    return all(
        fragment in boundaries
        for fragment in (
            "Proves only a live route foundation",
            "Does not grant suitability",
            "Does not create orders",
            "Does not promote a supported feature",
        )
    )


def _contract_retains_blockers(
    payload: dict[str, Any] | None, profile: RouteSourceContractProfile
) -> bool:
    return set(profile.remaining_blockers) <= set((payload or {}).get("certification_blockers", ()))


def _load_from_env(env_name: str) -> tuple[dict[str, Any] | None, str | None]:
    path_value = os.getenv(env_name)
    if not path_value:
        return None, None
    path = Path(path_value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{env_name} must reference a JSON object")
    try:
        artifact_ref = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        artifact_ref = f"{env_name} artifact"
    return payload, artifact_ref


def _optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None
