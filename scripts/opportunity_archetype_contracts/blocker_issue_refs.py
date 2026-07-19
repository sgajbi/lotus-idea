from __future__ import annotations

from app.application.opportunity_archetype_contracts import OpportunityArchetypeContract


SLICE_16_ISSUE_REF = "sgajbi/lotus-idea#696"


def validate_blocker_issue_refs(contract: OpportunityArchetypeContract) -> list[str]:
    errors: list[str] = []
    blockers = _contract_blockers(contract)
    issue_ref_blockers = set(contract.blocker_issue_refs)
    missing_mappings = sorted(blockers - issue_ref_blockers)
    if missing_mappings:
        errors.append(
            "opportunity archetype blocker_issue_refs missing blockers: "
            + ", ".join(missing_mappings)
        )
    stale_mappings = sorted(issue_ref_blockers - blockers)
    if stale_mappings:
        errors.append(
            "opportunity archetype blocker_issue_refs contains non-blockers: "
            + ", ".join(stale_mappings)
        )
    for blocker in sorted(blockers):
        _validate_blocker_issue_refs(
            blocker=blocker,
            issue_refs=contract.blocker_issue_refs.get(blocker, ()),
            errors=errors,
        )
    return errors


def _contract_blockers(contract: OpportunityArchetypeContract) -> set[str]:
    blockers: set[str] = set()
    for archetype in contract.archetypes:
        blockers.update(archetype.blockers)
        for scenario in archetype.canonical_scenarios:
            blockers.update(scenario.remaining_blockers)
    return blockers


def _validate_blocker_issue_refs(
    *,
    blocker: str,
    issue_refs: tuple[str, ...],
    errors: list[str],
) -> None:
    if not issue_refs:
        errors.append(f"opportunity archetype blocker_issue_refs.{blocker} is empty")
        return
    if SLICE_16_ISSUE_REF not in issue_refs:
        errors.append(
            f"opportunity archetype blocker_issue_refs.{blocker} missing Slice 16 issue "
            f"{SLICE_16_ISSUE_REF}"
        )
    invalid_refs = sorted(ref for ref in issue_refs if not _is_issue_ref(ref))
    if invalid_refs:
        errors.append(
            f"opportunity archetype blocker_issue_refs.{blocker} has invalid refs: "
            + ", ".join(invalid_refs)
        )


def _is_issue_ref(ref: str) -> bool:
    if not ref.startswith("sgajbi/") or "#" not in ref:
        return False
    _, number = ref.rsplit("#", maxsplit=1)
    return number.isdecimal()
