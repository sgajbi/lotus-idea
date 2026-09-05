from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain import (
    CausalInputRevision,
    OpportunityFamily,
    SourceCutPosture,
    SourceReconciliationPosture,
    SourceRevisionClaims,
)
from app.infrastructure.postgres_codecs import idea_candidate_from_json, idea_candidate_to_json
from tests.support.opportunity_effectiveness_fixture import candidate_fixture


def _candidate_with_revision_claims():
    candidate = candidate_fixture(
        "candidate-source-revision",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("82.00"),
        created_at=datetime(2026, 9, 4, 20, 1, tzinfo=UTC),
    )
    source = replace(
        candidate.evidence_packet.source_refs[0],
        revision_claims=SourceRevisionClaims(
            snapshot_id="snapshot-101",
            source_revision="portfolio-state-7",
            restatement_version="restatement-2",
            source_batch_id="core-close-2026-09-04",
            source_cut_id="close-2026-09-04",
            policy_version="portfolio-state-v4",
            causal_input_revisions=(
                CausalInputRevision(
                    product_id="lotus-core:HoldingsAsOf:v1",
                    source_revision="holdings-31",
                ),
            ),
            reconciliation_posture=SourceReconciliationPosture.COMPLETE,
        ),
    )
    packet = replace(
        candidate.evidence_packet,
        source_refs=(source,),
        lineage_ref=replace(candidate.evidence_packet.lineage_ref, source_refs=(source,)),
    )
    return replace(candidate, evidence_packet=packet)


def test_postgres_codec_round_trips_source_revision_identity_and_derived_posture() -> None:
    candidate = _candidate_with_revision_claims()

    payload = idea_candidate_to_json(candidate)
    restored = idea_candidate_from_json(payload)

    assert restored == candidate
    assert payload["evidence_packet"]["source_cut_posture"] == "coherent"
    assert payload["evidence_packet"]["source_revision_vector_digest"] == (
        candidate.evidence_packet.source_revision_vector_digest
    )


def test_postgres_codec_decodes_pre_migration_source_refs_as_explicit_unknown() -> None:
    payload = idea_candidate_to_json(_candidate_with_revision_claims())
    legacy_payload = deepcopy(payload)
    packet = legacy_payload["evidence_packet"]
    packet.pop("source_cut_posture")
    packet.pop("source_cut_tolerance")
    packet.pop("source_revision_vector_digest")
    packet["source_refs"][0].pop("revision_claims")
    packet["lineage_ref"]["source_refs"][0].pop("revision_claims")

    restored = idea_candidate_from_json(legacy_payload)

    assert restored.evidence_packet.source_cut_posture is SourceCutPosture.UNKNOWN
    assert restored.evidence_packet.source_refs[0].revision_claims is None


def test_postgres_codec_rejects_tampered_derived_revision_digest() -> None:
    payload = idea_candidate_to_json(_candidate_with_revision_claims())
    payload["evidence_packet"]["source_revision_vector_digest"] = "sha256:tampered"

    with pytest.raises(ValueError, match="revision vector digest does not match"):
        idea_candidate_from_json(payload)
