from __future__ import annotations

import importlib.util
from datetime import UTC, date, datetime
from pathlib import Path
from types import ModuleType

import pytest
from pydantic import ValidationError

from app.api.signal_models import ReviewAccessScopeRequest, SourceRefRequest
from app.domain import EvidenceFreshness, SourceSystem

ROOT = Path(__file__).resolve().parents[2]


def _load_api_signal_model_boundary_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "api_signal_model_boundary_gate.py"
    spec = importlib.util.spec_from_file_location("api_signal_model_boundary_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_review_access_scope_request_validates_and_maps_to_domain() -> None:
    request = ReviewAccessScopeRequest(
        tenantId="tenant-1",
        bookId="book-1",
        portfolioId="portfolio-1",
        clientId="client-1",
    )

    domain_scope = request.to_domain()

    assert domain_scope.tenant_id == "tenant-1"
    assert domain_scope.book_id == "book-1"
    assert domain_scope.portfolio_id == "portfolio-1"
    assert domain_scope.client_id == "client-1"


def test_review_access_scope_request_rejects_blank_scope_fields() -> None:
    with pytest.raises(ValidationError, match="scope fields cannot be blank"):
        ReviewAccessScopeRequest(
            tenantId="tenant-1",
            bookId=" ",
            portfolioId="portfolio-1",
            clientId="client-1",
        )


def test_source_ref_request_preserves_source_authority_metadata() -> None:
    request = SourceRefRequest(
        productId="lotus-core:PortfolioStateSnapshot:v1",
        sourceSystem=SourceSystem.LOTUS_CORE,
        productVersion="v1",
        route="/integration/portfolios/{portfolioRef}/core-snapshot",
        asOfDate=date(2026, 6, 21),
        generatedAtUtc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        contentHash="sha256:portfolio-state-snapshot-demo",
        dataQualityStatus="complete",
        freshness=EvidenceFreshness.CURRENT,
    )

    source_ref = request.to_domain()

    assert source_ref.product_id == "lotus-core:PortfolioStateSnapshot:v1"
    assert source_ref.source_system is SourceSystem.LOTUS_CORE
    assert source_ref.product_version == "v1"
    assert source_ref.route == "/integration/portfolios/{portfolioRef}/core-snapshot"
    assert source_ref.content_hash == "sha256:portfolio-state-snapshot-demo"
    assert source_ref.data_quality_status == "complete"
    assert source_ref.freshness is EvidenceFreshness.CURRENT


def test_api_signal_model_boundary_gate_passes_current_repository() -> None:
    module = _load_api_signal_model_boundary_gate()

    assert module.validate_api_signal_model_boundary() == []


def test_api_signal_model_boundary_gate_blocks_route_module_dto_import(tmp_path: Path) -> None:
    module = _load_api_signal_model_boundary_gate()
    api_dir = tmp_path / "src" / "app" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "unsafe_signal.py").write_text(
        "from app.api.idea_signals import SourceRefRequest, router\n",
        encoding="utf-8",
    )

    errors = module.validate_api_signal_model_boundary(tmp_path)

    assert errors == [
        "src/app/api/unsafe_signal.py:1: shared signal API DTOs (SourceRefRequest) must "
        "be imported from `app.api.signal_models`, not from the `idea_signals` route module"
    ]
