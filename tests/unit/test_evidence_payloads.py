from __future__ import annotations

from datetime import UTC, date, datetime

from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.domain.access_scope import ReviewAccessScope
from app.ports.evidence_payloads import access_scope_payload, source_ref_payload


def test_source_ref_payload_preserves_source_authority_fields() -> None:
    source_ref = SourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/api/v1/portfolios/p1/state",
        as_of_date=date(2026, 6, 21),
        generated_at_utc=datetime(2026, 6, 21, 10, 30, tzinfo=UTC),
        content_hash="sha256:portfolio-state",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )

    assert source_ref_payload(source_ref) == {
        "product_id": "lotus-core:PortfolioStateSnapshot:v1",
        "source_system": "lotus-core",
        "product_version": "v1",
        "route": "/api/v1/portfolios/p1/state",
        "as_of_date": "2026-06-21",
        "generated_at_utc": "2026-06-21T10:30:00+00:00",
        "content_hash": "sha256:portfolio-state",
        "data_quality_status": "complete",
        "freshness": "current",
    }


def test_access_scope_payload_preserves_private_banking_scope() -> None:
    scope = ReviewAccessScope(
        tenant_id="tenant-1",
        book_id="book-1",
        portfolio_id="portfolio-1",
        client_id="client-1",
    )

    assert access_scope_payload(scope) == {
        "tenant_id": "tenant-1",
        "book_id": "book-1",
        "portfolio_id": "portfolio-1",
        "client_id": "client-1",
    }
    assert access_scope_payload(None) is None
