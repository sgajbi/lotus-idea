from __future__ import annotations

from types import MappingProxyType
from typing import Mapping


REQUIRED_BLOCKER_ISSUE_REFS: Mapping[str, Mapping[str, frozenset[str]]] = MappingProxyType(
    {
        "lotus-idea-to-lotus-advise-proposal-intake:v1": MappingProxyType(
            {
                "suitability_policy_authority_remains_lotus_advise": frozenset(
                    {"sgajbi/lotus-idea#688", "sgajbi/lotus-advise#461"}
                ),
                "advise_live_contract_proof_missing": frozenset(
                    {"sgajbi/lotus-idea#688", "sgajbi/lotus-advise#461"}
                ),
            }
        ),
        "lotus-idea-to-lotus-manage-action-intake:v1": MappingProxyType(
            {
                "rebalance_execution_authority_remains_lotus_manage": frozenset(
                    {"sgajbi/lotus-idea#689", "sgajbi/lotus-manage#621"}
                ),
                "manage_live_contract_proof_missing": frozenset(
                    {"sgajbi/lotus-idea#689", "sgajbi/lotus-manage#621"}
                ),
            }
        ),
        "lotus-idea-to-lotus-report-evidence-pack-intake:v1": MappingProxyType(
            {
                "lotus_report_live_intake_route_proof_missing": frozenset(
                    {"sgajbi/lotus-idea#690", "sgajbi/lotus-report#152"}
                ),
                "report_evidence_pack_live_materialization_proof_missing": frozenset(
                    {"sgajbi/lotus-idea#690", "sgajbi/lotus-report#152"}
                ),
                "rendered_output_creation_missing": frozenset(
                    {"sgajbi/lotus-idea#690", "sgajbi/lotus-render#65"}
                ),
                "archive_record_creation_missing": frozenset(
                    {"sgajbi/lotus-idea#690", "sgajbi/lotus-archive#72"}
                ),
                "client_publication_authority_blocked": frozenset(
                    {"sgajbi/lotus-idea#690", "sgajbi/lotus-report#152"}
                ),
            }
        ),
    }
)

CAPABILITY_BLOCKER_ISSUE_REFS: Mapping[str, Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "advise-proposal-realization": MappingProxyType(
            {
                "suitability_policy_authority_remains_lotus_advise": (
                    "sgajbi/lotus-idea#688",
                    "sgajbi/lotus-advise#461",
                ),
                "advise_live_contract_proof_missing": (
                    "sgajbi/lotus-idea#688",
                    "sgajbi/lotus-advise#461",
                ),
            }
        ),
        "manage-action-realization": MappingProxyType(
            {
                "rebalance_execution_authority_remains_lotus_manage": (
                    "sgajbi/lotus-idea#689",
                    "sgajbi/lotus-manage#621",
                ),
                "manage_live_contract_proof_missing": (
                    "sgajbi/lotus-idea#689",
                    "sgajbi/lotus-manage#621",
                ),
            }
        ),
        "report-render-archive-realization": MappingProxyType(
            {
                "report_evidence_pack_live_materialization_proof_missing": (
                    "sgajbi/lotus-idea#690",
                    "sgajbi/lotus-report#152",
                ),
                "rendered_output_creation_missing": (
                    "sgajbi/lotus-idea#690",
                    "sgajbi/lotus-render#65",
                ),
                "archive_record_creation_missing": (
                    "sgajbi/lotus-idea#690",
                    "sgajbi/lotus-archive#72",
                ),
                "client_publication_authority_blocked": (
                    "sgajbi/lotus-idea#690",
                    "sgajbi/lotus-report#152",
                ),
            }
        ),
    }
)


def capability_blocker_issue_refs(
    capability_id: str,
) -> Mapping[str, tuple[str, ...]]:
    return CAPABILITY_BLOCKER_ISSUE_REFS[capability_id]


def validate_downstream_blocker_issue_refs(
    *,
    contract_id: str,
    blockers: tuple[str, ...],
    blocker_issue_refs: Mapping[str, tuple[str, ...]],
) -> list[str]:
    errors: list[str] = []
    blocker_set = set(blockers)
    expected_issue_refs = REQUIRED_BLOCKER_ISSUE_REFS[contract_id]
    missing_mappings = sorted(blocker_set - set(blocker_issue_refs))
    if missing_mappings:
        errors.append(
            f"{contract_id}: blocker_issue_refs missing blockers: " + ", ".join(missing_mappings)
        )
    stale_mappings = sorted(set(blocker_issue_refs) - blocker_set)
    if stale_mappings:
        errors.append(
            f"{contract_id}: blocker_issue_refs contains non-blockers: " + ", ".join(stale_mappings)
        )
    missing_expected = sorted(set(expected_issue_refs) - blocker_set)
    if missing_expected:
        errors.append(
            f"{contract_id}: blockers missing required issue-backed blocker keys: "
            + ", ".join(missing_expected)
        )
    for blocker, required_refs in sorted(expected_issue_refs.items()):
        actual_refs = set(blocker_issue_refs.get(blocker, ()))
        missing_refs = sorted(required_refs - actual_refs)
        if missing_refs:
            errors.append(
                f"{contract_id}: blocker_issue_refs.{blocker} missing required issue refs: "
                + ", ".join(missing_refs)
            )
        if not all(_is_github_issue_ref(ref) for ref in actual_refs):
            errors.append(
                f"{contract_id}: blocker_issue_refs.{blocker} must use sgajbi/<repo>#<number> refs"
            )
    return errors


def _is_github_issue_ref(issue_ref: str) -> bool:
    if not issue_ref.startswith("sgajbi/") or "#" not in issue_ref:
        return False
    repository, number = issue_ref.split("#", maxsplit=1)
    return bool(repository.removeprefix("sgajbi/")) and number.isdigit()
