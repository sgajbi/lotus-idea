from __future__ import annotations

from typing import Any


def coherent_lotus_core_revision_claims(
    product_id: str,
    *,
    suffix: str = "",
) -> dict[str, str]:
    """Return one owner-issued revision claim from a coherent Core source cut."""

    return {
        "sourceRevision": f"revision:{product_id}{suffix}",
        "sourceCutId": f"core-close-2026-06-21{suffix}",
        "reconciliationPosture": "complete",
    }


def lotus_core_source_ref(
    product_id: str,
    *,
    suffix: str = "",
    freshness: str = "current",
) -> dict[str, Any]:
    """Build a deterministic Core source reference with coherent revision authority."""

    return {
        "productId": product_id,
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "route": f"/source/{product_id}",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}{suffix}",
        "dataQualityStatus": "complete",
        "freshness": freshness,
        "revisionClaims": coherent_lotus_core_revision_claims(product_id, suffix=suffix),
    }


__all__ = ["coherent_lotus_core_revision_claims", "lotus_core_source_ref"]
