from __future__ import annotations

from app.api.candidate_detail_models import CandidateDetailResponse
from app.domain import CandidatePersistenceRecord
from tests.unit.test_postgres_repository import access_scope, high_cash_candidate


def test_candidate_detail_response_redacts_source_routes_and_content_hashes() -> None:
    candidate = high_cash_candidate(candidate_scope=access_scope())
    record = CandidatePersistenceRecord(
        candidate=candidate,
        evidence_hash="sha256:candidate-detail",
        persisted_at_utc=candidate.created_at_utc,
    )

    response = CandidateDetailResponse.from_record(
        record,
        durable_storage_backed=True,
    ).model_dump(by_alias=True)

    assert response["candidate"]["candidateId"] == candidate.candidate_id
    assert response["evidence"]["evidenceContentHash"] == "sha256:candidate-detail"
    assert response["evidence"]["sourceRefs"][0] == {
        "productId": "lotus-core:PortfolioStateSnapshot:v1",
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "asOfDate": candidate.evidence_packet.source_refs[0].as_of_date,
        "generatedAtUtc": candidate.evidence_packet.source_refs[0].generated_at_utc,
        "dataQualityStatus": "complete",
        "freshness": "current",
    }
    assert "route" not in response["evidence"]["sourceRefs"][0]
    assert "contentHash" not in response["evidence"]["sourceRefs"][0]
    assert response["durableStorageBacked"] is True
    assert response["supportedFeaturePromoted"] is False
