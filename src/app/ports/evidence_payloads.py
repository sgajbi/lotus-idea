from __future__ import annotations

from typing import Any

from app.domain import SourceRef
from app.domain.access_scope import ReviewAccessScope


def source_ref_payload(source_ref: SourceRef) -> dict[str, Any]:
    return {
        "product_id": source_ref.product_id,
        "source_system": source_ref.source_system.value,
        "product_version": source_ref.product_version,
        "route": source_ref.route,
        "as_of_date": source_ref.as_of_date.isoformat(),
        "generated_at_utc": source_ref.generated_at_utc.isoformat(),
        "content_hash": source_ref.content_hash,
        "data_quality_status": source_ref.data_quality_status,
        "freshness": source_ref.freshness.value,
    }


def access_scope_payload(scope: ReviewAccessScope | None) -> dict[str, Any] | None:
    if scope is None:
        return None
    return {
        "tenant_id": scope.tenant_id,
        "book_id": scope.book_id,
        "portfolio_id": scope.portfolio_id,
        "client_id": scope.client_id,
    }
