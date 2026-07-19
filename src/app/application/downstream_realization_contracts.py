from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, cast


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DOWNSTREAM_CONTRACT_PLAN_PATH = Path(
    "contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json"
)


@dataclass(frozen=True)
class DownstreamRealizationContractPlanRecord:
    contract_id: str
    owner_repository: str
    source_authority: str
    target_route: str
    route_fit_status: str
    adapter_status: str
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    blocker_issue_refs: Mapping[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "blockers", tuple(self.blockers))
        object.__setattr__(
            self,
            "blocker_issue_refs",
            MappingProxyType(
                {
                    str(blocker): tuple(issue_refs)
                    for blocker, issue_refs in self.blocker_issue_refs.items()
                }
            ),
        )


@dataclass(frozen=True)
class DownstreamRealizationContractPlan:
    contract_id: str
    contract_version: str
    repository: str
    lifecycle_status: str
    supportability_status: str
    route_existence_proven: bool
    downstream_execution_proven: bool
    supported_feature_promoted: bool
    source_of_truth: Mapping[str, str]
    contracts: tuple[DownstreamRealizationContractPlanRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_of_truth", MappingProxyType(dict(self.source_of_truth)))
        object.__setattr__(self, "contracts", tuple(self.contracts))


def load_downstream_realization_contract_plan(
    *,
    repository_root: Path = REPOSITORY_ROOT,
    contract_path: Path = DOWNSTREAM_CONTRACT_PLAN_PATH,
) -> DownstreamRealizationContractPlan:
    payload = json.loads((repository_root / contract_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("downstream realization contract plan must be a JSON object")
    return downstream_realization_contract_plan_from_payload(payload)


def downstream_realization_contract_plan_from_payload(
    payload: Mapping[str, Any],
) -> DownstreamRealizationContractPlan:
    source_of_truth = payload.get("source_of_truth", {})
    contracts = payload.get("contracts", ())
    if not isinstance(source_of_truth, dict):
        raise ValueError("downstream realization source_of_truth must be an object")
    if not isinstance(contracts, list):
        raise ValueError("downstream realization contracts must be a list")
    if not all(isinstance(contract, dict) for contract in contracts):
        raise ValueError("downstream realization contract entries must be objects")

    return DownstreamRealizationContractPlan(
        contract_id=str(payload.get("contract_id", "")),
        contract_version=str(payload.get("contract_version", "")),
        repository=str(payload.get("repository", "")),
        lifecycle_status=str(payload.get("lifecycle_status", "")),
        supportability_status=str(payload.get("supportability_status", "")),
        route_existence_proven=bool(payload.get("route_existence_proven", True)),
        downstream_execution_proven=bool(payload.get("downstream_execution_proven", True)),
        supported_feature_promoted=bool(payload.get("supported_feature_promoted", True)),
        source_of_truth={str(key): str(value) for key, value in source_of_truth.items()},
        contracts=tuple(
            _contract_record_from_payload(cast(Mapping[str, Any], contract))
            for contract in contracts
        ),
    )


def _contract_record_from_payload(
    payload: Mapping[str, Any],
) -> DownstreamRealizationContractPlanRecord:
    return DownstreamRealizationContractPlanRecord(
        contract_id=str(payload.get("contract_id", "")),
        owner_repository=str(payload.get("owner_repository", "")),
        source_authority=str(payload.get("source_authority", "")),
        target_route=str(payload.get("target_route", "")),
        route_fit_status=str(payload.get("route_fit_status", "")),
        adapter_status=str(payload.get("adapter_status", "")),
        evidence_refs=_strings(payload.get("evidence_refs", ())),
        blockers=_strings(payload.get("blockers", ())),
        blocker_issue_refs=_string_tuple_mapping(payload.get("blocker_issue_refs", {})),
    )


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def _string_tuple_mapping(value: object) -> Mapping[str, tuple[str, ...]]:
    if not isinstance(value, dict):
        return {}
    parsed: dict[str, tuple[str, ...]] = {}
    for key, refs in value.items():
        if not isinstance(refs, list):
            parsed[str(key)] = ()
            continue
        parsed[str(key)] = tuple(str(ref) for ref in refs)
    return parsed
