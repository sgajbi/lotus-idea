from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from app.domain.ideas import (
    OpportunityFamily,
    ReasonCode,
    SourceRef,
    UnsupportedEvidenceReason,
)


SOURCE_TEMPORAL_CONTRACT_VERSION = "idea-source-temporal-v1"


class SourceBusinessDateRule(StrEnum):
    EXACT_REQUEST_DATE = "exact_request_date"


class SourceGeneratedTimeRule(StrEnum):
    NOT_AFTER_EVALUATION = "not_after_evaluation"


class SourceCorrectionIdentityRule(StrEnum):
    NEW_CONTENT_HASH_CREATES_NEW_CANDIDATE_IDENTITY = (
        "new_content_hash_creates_new_candidate_identity"
    )


@dataclass(frozen=True)
class SourceTemporalContract:
    contract_version: str
    family: OpportunityFamily
    business_date_rule: SourceBusinessDateRule
    generated_time_rule: SourceGeneratedTimeRule
    correction_identity_rule: SourceCorrectionIdentityRule


SOURCE_TEMPORAL_CONTRACTS: Mapping[OpportunityFamily, SourceTemporalContract] = MappingProxyType(
    {
        family: SourceTemporalContract(
            contract_version=SOURCE_TEMPORAL_CONTRACT_VERSION,
            family=family,
            business_date_rule=SourceBusinessDateRule.EXACT_REQUEST_DATE,
            generated_time_rule=SourceGeneratedTimeRule.NOT_AFTER_EVALUATION,
            correction_identity_rule=(
                SourceCorrectionIdentityRule.NEW_CONTENT_HASH_CREATES_NEW_CANDIDATE_IDENTITY
            ),
        )
        for family in OpportunityFamily
    }
)


def source_temporal_contract_for(family: OpportunityFamily) -> SourceTemporalContract:
    return SOURCE_TEMPORAL_CONTRACTS[family]


def source_temporal_violation(
    *,
    family: OpportunityFamily,
    requested_as_of_date: date,
    evaluated_at_utc: datetime,
    source_refs: tuple[SourceRef, ...],
) -> tuple[ReasonCode, UnsupportedEvidenceReason] | None:
    """Return the first deterministic source-time contract violation."""
    contract = source_temporal_contract_for(family)
    for source_ref in source_refs:
        if (
            contract.business_date_rule is SourceBusinessDateRule.EXACT_REQUEST_DATE
            and source_ref.as_of_date != requested_as_of_date
        ):
            return (
                ReasonCode.SOURCE_DATE_MISMATCH,
                UnsupportedEvidenceReason.SOURCE_TEMPORAL_MISMATCH,
            )
        if (
            contract.generated_time_rule is SourceGeneratedTimeRule.NOT_AFTER_EVALUATION
            and source_ref.generated_at_utc > evaluated_at_utc
        ):
            return (
                ReasonCode.SOURCE_GENERATED_AFTER_EVALUATION,
                UnsupportedEvidenceReason.SOURCE_TEMPORAL_MISMATCH,
            )
    return None
