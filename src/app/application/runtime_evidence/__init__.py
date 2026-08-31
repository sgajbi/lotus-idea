"""Shared primitives for receipt-bound runtime evidence."""

from .contract import SCORE_RECEIPT_KEYS, non_authority_claims_are_valid, score_receipt_is_valid
from .receipts import (
    format_utc,
    identity_hash,
    require_aware,
    score_receipt,
    sha256_json,
    source_ref_material,
    source_ref_receipt,
)
from .scope import RuntimeEvidenceScope

__all__ = [
    "RuntimeEvidenceScope",
    "SCORE_RECEIPT_KEYS",
    "format_utc",
    "identity_hash",
    "non_authority_claims_are_valid",
    "require_aware",
    "score_receipt",
    "score_receipt_is_valid",
    "sha256_json",
    "source_ref_material",
    "source_ref_receipt",
]
