from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.advise_source_product_evidence.contract import (
    MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_ENV,
    MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_ENV,
    SCHEMA_VERSION,
    advise_source_product_source_contract_is_valid,
    build_advise_source_product_source_contract,
)
from app.application.advise_source_product_evidence.profiles import (
    MANDATE_RESTRICTION_PROFILE,
    MISSING_RISK_PROFILE,
    PROFILES,
    AdviseSourceProductProfile,
)


MANDATE_RESTRICTION_SOURCE_PRODUCT_BLOCKERS_CLEARED = MANDATE_RESTRICTION_PROFILE.blockers_satisfied
MISSING_RISK_PROFILE_SOURCE_PRODUCT_BLOCKERS_CLEARED = MISSING_RISK_PROFILE.blockers_satisfied


def build_mandate_restriction_source_product_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    advise_root: Path | None = None,
) -> dict[str, Any]:
    return build_advise_source_product_source_contract(
        profile=MANDATE_RESTRICTION_PROFILE,
        generated_at_utc=generated_at_utc,
        repository_root=repository_root,
        advise_root=advise_root,
    )


def mandate_restriction_source_product_proof_is_valid(payload: object) -> bool:
    from collections.abc import Mapping

    return isinstance(payload, Mapping) and advise_source_product_source_contract_is_valid(
        payload,
        profile=MANDATE_RESTRICTION_PROFILE,
    )


def build_missing_risk_profile_source_product_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    advise_root: Path | None = None,
) -> dict[str, Any]:
    return build_advise_source_product_source_contract(
        profile=MISSING_RISK_PROFILE,
        generated_at_utc=generated_at_utc,
        repository_root=repository_root,
        advise_root=advise_root,
    )


def missing_risk_profile_source_product_proof_is_valid(payload: object) -> bool:
    from collections.abc import Mapping

    return isinstance(payload, Mapping) and advise_source_product_source_contract_is_valid(
        payload,
        profile=MISSING_RISK_PROFILE,
    )


__all__ = [
    "AdviseSourceProductProfile",
    "MANDATE_RESTRICTION_PROFILE",
    "MANDATE_RESTRICTION_SOURCE_PRODUCT_BLOCKERS_CLEARED",
    "MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_ENV",
    "MISSING_RISK_PROFILE",
    "MISSING_RISK_PROFILE_SOURCE_PRODUCT_BLOCKERS_CLEARED",
    "MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_ENV",
    "PROFILES",
    "SCHEMA_VERSION",
    "advise_source_product_source_contract_is_valid",
    "build_advise_source_product_source_contract",
    "build_mandate_restriction_source_product_proof_payload",
    "build_missing_risk_profile_source_product_proof_payload",
    "mandate_restriction_source_product_proof_is_valid",
    "missing_risk_profile_source_product_proof_is_valid",
]
