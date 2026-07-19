from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, cast


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
OPPORTUNITY_ARCHETYPE_CONTRACT_PATH = Path(
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json"
)


@dataclass(frozen=True)
class OpportunityScenarioRecord:
    scenario_id: str
    scenario_status: str
    scenario_type: str
    audience: str
    proof_status: str
    supported_feature_promoted: bool
    required_evidence: tuple[str, ...]
    remaining_blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_evidence", tuple(self.required_evidence))
        object.__setattr__(self, "remaining_blockers", tuple(self.remaining_blockers))


@dataclass(frozen=True)
class OpportunityArchetypeRecord:
    archetype_id: str
    display_name: str
    implementation_status: str
    source_authority_status: str
    first_supported_journey: bool
    advisor_audience: str
    source_products: tuple[str, ...]
    lotus_idea_responsibility: str
    evidence_refs: tuple[str, ...]
    canonical_scenarios: tuple[OpportunityScenarioRecord, ...]
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_products", tuple(self.source_products))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "canonical_scenarios", tuple(self.canonical_scenarios))
        object.__setattr__(self, "blockers", tuple(self.blockers))


@dataclass(frozen=True)
class OpportunityArchetypeContract:
    contract_id: str
    contract_version: str
    repository: str
    lifecycle_status: str
    supportability_status: str
    canonical_portfolio_ref: str
    demo_ready: bool
    client_publication_ready: bool
    supported_feature_promoted: bool
    data_mesh_certified: bool
    source_of_truth: Mapping[str, str]
    blocker_issue_refs: Mapping[str, tuple[str, ...]]
    archetypes: tuple[OpportunityArchetypeRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_of_truth", MappingProxyType(dict(self.source_of_truth)))
        object.__setattr__(
            self,
            "blocker_issue_refs",
            MappingProxyType(
                {
                    blocker: tuple(issue_refs)
                    for blocker, issue_refs in self.blocker_issue_refs.items()
                }
            ),
        )
        object.__setattr__(self, "archetypes", tuple(self.archetypes))


def load_opportunity_archetype_contract(
    *,
    repository_root: Path = REPOSITORY_ROOT,
    contract_path: Path = OPPORTUNITY_ARCHETYPE_CONTRACT_PATH,
) -> OpportunityArchetypeContract:
    payload = json.loads((repository_root / contract_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("opportunity archetype contract must be a JSON object")
    return opportunity_archetype_contract_from_payload(payload)


def opportunity_archetype_contract_from_payload(
    payload: Mapping[str, Any],
) -> OpportunityArchetypeContract:
    source_of_truth = payload.get("source_of_truth", {})
    blocker_issue_refs = payload.get("blocker_issue_refs", {})
    archetypes = payload.get("archetypes", ())
    if not isinstance(source_of_truth, dict):
        raise ValueError("opportunity archetype source_of_truth must be an object")
    if not isinstance(blocker_issue_refs, dict):
        raise ValueError("opportunity archetype blocker_issue_refs must be an object")
    if not isinstance(archetypes, list):
        raise ValueError("opportunity archetypes must be a list")
    if not all(isinstance(archetype, dict) for archetype in archetypes):
        raise ValueError("opportunity archetype entries must be objects")

    return OpportunityArchetypeContract(
        contract_id=str(payload.get("contract_id", "")),
        contract_version=str(payload.get("contract_version", "")),
        repository=str(payload.get("repository", "")),
        lifecycle_status=str(payload.get("lifecycle_status", "")),
        supportability_status=str(payload.get("supportability_status", "")),
        canonical_portfolio_ref=str(payload.get("canonical_portfolio_ref", "")),
        demo_ready=bool(payload.get("demo_ready", True)),
        client_publication_ready=bool(payload.get("client_publication_ready", True)),
        supported_feature_promoted=bool(payload.get("supported_feature_promoted", True)),
        data_mesh_certified=bool(payload.get("data_mesh_certified", True)),
        source_of_truth={str(key): str(value) for key, value in source_of_truth.items()},
        blocker_issue_refs=_string_tuple_mapping(blocker_issue_refs),
        archetypes=tuple(
            _archetype_from_payload(cast(Mapping[str, Any], archetype)) for archetype in archetypes
        ),
    )


def _archetype_from_payload(payload: Mapping[str, Any]) -> OpportunityArchetypeRecord:
    scenarios = payload.get("canonical_scenarios", ())
    return OpportunityArchetypeRecord(
        archetype_id=str(payload.get("archetype_id", "")),
        display_name=str(payload.get("display_name", "")),
        implementation_status=str(payload.get("implementation_status", "")),
        source_authority_status=str(payload.get("source_authority_status", "")),
        first_supported_journey=bool(payload.get("first_supported_journey", False)),
        advisor_audience=str(payload.get("advisor_audience", "")),
        source_products=_strings(payload.get("source_products", ())),
        lotus_idea_responsibility=str(payload.get("lotus_idea_responsibility", "")),
        evidence_refs=_strings(payload.get("evidence_refs", ())),
        canonical_scenarios=tuple(
            _scenario_from_payload(cast(Mapping[str, Any], scenario))
            for scenario in scenarios
            if isinstance(scenario, dict)
        ),
        blockers=_strings(payload.get("blockers", ())),
    )


def _scenario_from_payload(payload: Mapping[str, Any]) -> OpportunityScenarioRecord:
    return OpportunityScenarioRecord(
        scenario_id=str(payload.get("scenario_id", "")),
        scenario_status=str(payload.get("scenario_status", "")),
        scenario_type=str(payload.get("scenario_type", "")),
        audience=str(payload.get("audience", "")),
        proof_status=str(payload.get("proof_status", "")),
        supported_feature_promoted=bool(payload.get("supported_feature_promoted", True)),
        required_evidence=_strings(payload.get("required_evidence", ())),
        remaining_blockers=_strings(payload.get("remaining_blockers", ())),
    )


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def _string_tuple_mapping(value: Mapping[str, Any]) -> Mapping[str, tuple[str, ...]]:
    return {str(key): _strings(item) for key, item in value.items()}
