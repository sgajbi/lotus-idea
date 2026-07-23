from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from app.application.opportunity_archetype_contracts import (
    OPPORTUNITY_ARCHETYPE_CONTRACT_PATH,
    OpportunityArchetypeContract,
    OpportunityArchetypeRecord,
    OpportunityScenarioRecord,
    load_opportunity_archetype_contract,
)
from app.domain.proof_evidence import EvidenceClass, parse_timezone_aware_datetime

CANONICAL_PORTFOLIO_REF = "PB_SG_GLOBAL_BAL_001"
OPPORTUNITY_ARCHETYPE_EVIDENCE_PACK_ENV = "LOTUS_IDEA_OPPORTUNITY_ARCHETYPE_EVIDENCE_PACK"
OPPORTUNITY_ARCHETYPE_EVIDENCE_PACK_SCHEMA_VERSION = (
    "lotus-idea.opportunity-archetype.evidence-pack.v1"
)
OPPORTUNITY_ARCHETYPE_EVIDENCE_PACK_OUTPUT_PATH = Path(
    "output/opportunity/canonical-archetype-evidence-pack.json"
)
OPPORTUNITY_ARCHETYPE_EVIDENCE_PACK_REFS = (
    "src/app/application/opportunity_archetype_evidence_pack.py",
    "scripts/opportunity_archetype_evidence_pack/generate_evidence_pack.py",
    "scripts/opportunity_archetype_evidence_pack/evidence_pack_contract_gate.py",
    "make opportunity-archetype-evidence-pack-gate",
)
_EXPECTED_TOP_LEVEL_KEYS = frozenset(
    {
        "schemaVersion",
        "repository",
        "rfc",
        "rfcSlice",
        "generatedAtUtc",
        "evidenceClass",
        "proofFamily",
        "proofType",
        "sourceAuthorityBoundary",
        "canonicalPortfolioScope",
        "claimBoundary",
        "sourceOfTruth",
        "packSummary",
        "archetypeEvidence",
        "remainingCertificationBlockers",
        "evidenceRefs",
        "aggregateProofProvenance",
    }
)
_FORBIDDEN_SOURCE_TEXT = (
    CANONICAL_PORTFOLIO_REF,
    "tenant-a",
    "portfolio-a",
    "client-001",
    "corr-a",
)


def build_canonical_opportunity_archetype_evidence_pack(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")

    contract = load_opportunity_archetype_contract(repository_root=repository_root)
    if contract.canonical_portfolio_ref != CANONICAL_PORTFOLIO_REF:
        raise ValueError("opportunity archetype contract is not bound to the canonical portfolio")

    archetype_evidence = tuple(
        _archetype_evidence(archetype, contract) for archetype in contract.archetypes
    )
    blockers = tuple(
        dict.fromkeys(
            blocker
            for archetype in archetype_evidence
            for blocker in archetype["remainingBlockers"]
        )
    )
    payload: dict[str, Any] = {
        "schemaVersion": OPPORTUNITY_ARCHETYPE_EVIDENCE_PACK_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "rfc": "RFC-0002",
        "rfcSlice": "slice-16",
        "generatedAtUtc": _format_utc(generated_at_utc),
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "proofFamily": "opportunity_archetype",
        "proofType": "canonical_archetype_evidence_pack",
        "sourceAuthorityBoundary": {
            "lotusIdeaOwns": (
                "opportunity detection, idea lifecycle, evidence-pack composition, "
                "scoring, review workflow, feedback, conversion intent, and readiness posture"
            ),
            "sourceAuthoritiesRemainOwnedBy": (
                "lotus-core, lotus-risk, lotus-performance, lotus-advise, lotus-manage, "
                "lotus-report, lotus-render, lotus-archive, and lotus-ai"
            ),
            "sourceCalculationsPerformedByLotusIdea": False,
        },
        "canonicalPortfolioScope": {
            "scopeId": "canonical-front-office-private-bank-balanced-portfolio",
            "sourceRefHandling": "canonical portfolio reference hashed and not serialized",
            "sourceRefSha256": _sha256_text(CANONICAL_PORTFOLIO_REF),
            "governedDatasetRefs": [
                "lotus-platform/context/contracts/canonical-front-office-demo-data-contract.json",
                "lotus-platform/context/contracts/canonical-front-office-demo-data-invariants.json",
            ],
        },
        "claimBoundary": {
            "supportabilityStatus": "not_certified",
            "readinessStatus": "blocked",
            "demoReady": False,
            "clientPublicationReady": False,
            "supportedFeaturePromoted": False,
            "dataMeshCertified": False,
            "productionIdentityCertified": False,
            "commercialClaimAllowed": "internal_foundation_walkthrough_only",
        },
        "sourceOfTruth": {
            "archetypeContract": OPPORTUNITY_ARCHETYPE_CONTRACT_PATH.as_posix(),
            "implementationProofReadiness": "src/app/application/implementation_proof_readiness.py",
            "rfcSlice16": (
                "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
                "RFC-0002-slice-16-demo-readiness-archetype-scenarios-and-commercial-proof.md"
            ),
            "issue": "sgajbi/lotus-idea#696",
            **dict(contract.source_of_truth),
        },
        "packSummary": {
            "archetypeCount": len(archetype_evidence),
            "boundedFoundationCount": sum(
                1
                for archetype in archetype_evidence
                if archetype["classification"] == "bounded_foundation"
            ),
            "plannedCount": sum(
                1 for archetype in archetype_evidence if archetype["classification"] == "planned"
            ),
            "supportedCount": 0,
            "scenarioCount": sum(
                len(archetype["canonicalScenarios"]) for archetype in archetype_evidence
            ),
            "blockerCount": len(blockers),
        },
        "archetypeEvidence": list(archetype_evidence),
        "remainingCertificationBlockers": list(blockers),
        "evidenceRefs": list(
            dict.fromkeys(
                (
                    OPPORTUNITY_ARCHETYPE_CONTRACT_PATH.as_posix(),
                    *OPPORTUNITY_ARCHETYPE_EVIDENCE_PACK_REFS,
                    "docs/demo/demo-claims.md",
                    "docs/operations/implementation-proof-readiness.md",
                    "wiki/Demo-Readiness.md",
                )
            )
        ),
    }
    payload["packDigest"] = _sha256_json_without_pack_digest(payload)
    return payload


def opportunity_archetype_evidence_pack_is_valid(payload: Mapping[str, object]) -> bool:
    return not validate_opportunity_archetype_evidence_pack_payload(payload)


def validate_opportunity_archetype_evidence_pack_payload(
    payload: Mapping[str, object],
    *,
    repository_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    _validate_top_level(payload, errors)
    _validate_source_safety(payload, errors)
    generated_at_utc = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    if generated_at_utc is None:
        errors.append("generatedAtUtc must be timezone-aware")
    if payload.get("schemaVersion") != OPPORTUNITY_ARCHETYPE_EVIDENCE_PACK_SCHEMA_VERSION:
        errors.append("schemaVersion must be lotus-idea.opportunity-archetype.evidence-pack.v1")
    if payload.get("repository") != "lotus-idea":
        errors.append("repository must be lotus-idea")
    if payload.get("rfc") != "RFC-0002" or payload.get("rfcSlice") != "slice-16":
        errors.append("evidence pack must be bound to RFC-0002 slice-16")
    if payload.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        errors.append("evidenceClass must be source_contract")
    if payload.get("proofFamily") != "opportunity_archetype":
        errors.append("proofFamily must be opportunity_archetype")
    if payload.get("proofType") != "canonical_archetype_evidence_pack":
        errors.append("proofType must be canonical_archetype_evidence_pack")
    _validate_claim_boundary(payload.get("claimBoundary"), errors)
    _validate_canonical_scope(payload.get("canonicalPortfolioScope"), errors)

    contract = load_opportunity_archetype_contract(
        repository_root=repository_root or Path(__file__).resolve().parents[3],
    )
    _validate_against_contract(payload, contract, errors)
    return errors


def _archetype_evidence(
    archetype: OpportunityArchetypeRecord,
    contract: OpportunityArchetypeContract,
) -> dict[str, Any]:
    blockers = tuple(
        dict.fromkeys(
            (
                *archetype.blockers,
                *(
                    blocker
                    for scenario in archetype.canonical_scenarios
                    for blocker in scenario.remaining_blockers
                ),
            )
        )
    )
    return {
        "archetypeId": archetype.archetype_id,
        "displayName": archetype.display_name,
        "classification": _classification(archetype),
        "implementationStatus": archetype.implementation_status,
        "sourceAuthorityStatus": archetype.source_authority_status,
        "firstSupportedJourney": archetype.first_supported_journey,
        "advisorAudience": archetype.advisor_audience,
        "sourceProducts": list(archetype.source_products),
        "lotusIdeaResponsibility": archetype.lotus_idea_responsibility,
        "evidenceRefs": list(archetype.evidence_refs),
        "canonicalScenarios": [
            _scenario_evidence(scenario) for scenario in archetype.canonical_scenarios
        ],
        "remainingBlockers": list(blockers),
        "blockerIssueRefs": {
            blocker: list(contract.blocker_issue_refs[blocker])
            for blocker in blockers
            if blocker in contract.blocker_issue_refs
        },
        "claimBoundary": {
            "scenarioProofStatus": "not_client_demo_ready",
            "sourceAuthorityTransferred": False,
            "supportedFeaturePromoted": False,
        },
    }


def _scenario_evidence(scenario: OpportunityScenarioRecord) -> dict[str, Any]:
    return {
        "scenarioId": scenario.scenario_id,
        "scenarioStatus": scenario.scenario_status,
        "scenarioType": scenario.scenario_type,
        "audience": scenario.audience,
        "proofStatus": scenario.proof_status,
        "supportedFeaturePromoted": scenario.supported_feature_promoted,
        "requiredEvidence": list(scenario.required_evidence),
        "remainingBlockers": list(scenario.remaining_blockers),
    }


def _classification(archetype: OpportunityArchetypeRecord) -> str:
    if archetype.implementation_status == "partially_implemented":
        return "bounded_foundation"
    return "planned"


def _validate_top_level(payload: Mapping[str, object], errors: list[str]) -> None:
    unknown_keys = sorted(set(payload) - _EXPECTED_TOP_LEVEL_KEYS - {"packDigest"})
    if unknown_keys:
        errors.append(f"unexpected evidence pack fields: {', '.join(unknown_keys)}")
    required = _EXPECTED_TOP_LEVEL_KEYS - {"aggregateProofProvenance"}
    missing = sorted(key for key in required if key not in payload)
    if missing:
        errors.append(f"missing evidence pack fields: {', '.join(missing)}")


def _validate_source_safety(payload: Mapping[str, object], errors: list[str]) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    for forbidden in _FORBIDDEN_SOURCE_TEXT:
        if forbidden in serialized:
            errors.append(f"forbidden source-sensitive text `{forbidden}` is present")


def _validate_claim_boundary(value: object, errors: list[str]) -> None:
    if not isinstance(value, Mapping):
        errors.append("claimBoundary must be an object")
        return
    for field in (
        "demoReady",
        "clientPublicationReady",
        "supportedFeaturePromoted",
        "dataMeshCertified",
        "productionIdentityCertified",
    ):
        if value.get(field) is not False:
            errors.append(f"claimBoundary.{field} must be false")
    if value.get("supportabilityStatus") != "not_certified":
        errors.append("claimBoundary.supportabilityStatus must be not_certified")
    if value.get("readinessStatus") != "blocked":
        errors.append("claimBoundary.readinessStatus must be blocked")


def _validate_canonical_scope(value: object, errors: list[str]) -> None:
    if not isinstance(value, Mapping):
        errors.append("canonicalPortfolioScope must be an object")
        return
    if value.get("sourceRefSha256") != _sha256_text(CANONICAL_PORTFOLIO_REF):
        errors.append("canonicalPortfolioScope.sourceRefSha256 does not match canonical scope")
    refs = value.get("governedDatasetRefs")
    if not isinstance(refs, list) or not refs:
        errors.append("canonicalPortfolioScope.governedDatasetRefs must be a non-empty list")


def _validate_against_contract(
    payload: Mapping[str, object],
    contract: OpportunityArchetypeContract,
    errors: list[str],
) -> None:
    if contract.demo_ready or contract.client_publication_ready:
        errors.append("source contract must not claim demo or client-publication readiness")
    if contract.supported_feature_promoted or contract.data_mesh_certified:
        errors.append("source contract must not claim supported-feature or data-mesh certification")
    if contract.canonical_portfolio_ref != CANONICAL_PORTFOLIO_REF:
        errors.append("source contract canonical portfolio ref is unexpected")

    archetype_evidence = payload.get("archetypeEvidence")
    if not isinstance(archetype_evidence, list):
        errors.append("archetypeEvidence must be a list")
        return
    evidence_by_id = {
        item.get("archetypeId"): item for item in archetype_evidence if isinstance(item, Mapping)
    }
    expected_ids = tuple(archetype.archetype_id for archetype in contract.archetypes)
    if set(evidence_by_id) != set(expected_ids):
        errors.append("archetypeEvidence must contain exactly the contract archetypes")
        return
    for archetype in contract.archetypes:
        _validate_archetype_against_contract(
            evidence_by_id[archetype.archetype_id],
            archetype,
            contract,
            errors,
        )


def _validate_archetype_against_contract(
    evidence: object,
    archetype: OpportunityArchetypeRecord,
    contract: OpportunityArchetypeContract,
    errors: list[str],
) -> None:
    if not isinstance(evidence, Mapping):
        errors.append(f"{archetype.archetype_id}: evidence entry must be an object")
        return
    expected_blockers = tuple(
        dict.fromkeys(
            (
                *archetype.blockers,
                *(
                    blocker
                    for scenario in archetype.canonical_scenarios
                    for blocker in scenario.remaining_blockers
                ),
            )
        )
    )
    if evidence.get("classification") == "supported":
        errors.append(f"{archetype.archetype_id}: classification must not be supported")
    if tuple(evidence.get("sourceProducts", ())) != archetype.source_products:
        errors.append(f"{archetype.archetype_id}: sourceProducts do not match contract")
    if tuple(evidence.get("evidenceRefs", ())) != archetype.evidence_refs:
        errors.append(f"{archetype.archetype_id}: evidenceRefs do not match contract")
    if tuple(evidence.get("remainingBlockers", ())) != expected_blockers:
        errors.append(f"{archetype.archetype_id}: remainingBlockers do not match contract")
    blocker_issue_refs = evidence.get("blockerIssueRefs")
    if not isinstance(blocker_issue_refs, Mapping):
        errors.append(f"{archetype.archetype_id}: blockerIssueRefs must be an object")
        return
    missing_refs = [
        blocker
        for blocker in expected_blockers
        if tuple(blocker_issue_refs.get(blocker, ())) != contract.blocker_issue_refs.get(blocker)
    ]
    if missing_refs:
        errors.append(
            f"{archetype.archetype_id}: blockerIssueRefs missing or mismatched for "
            f"{', '.join(missing_refs)}"
        )


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json_without_pack_digest(payload: Mapping[str, object]) -> str:
    material = {key: value for key, value in payload.items() if key != "packDigest"}
    serialized = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
