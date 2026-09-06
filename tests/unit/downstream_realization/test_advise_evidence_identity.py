from __future__ import annotations

from app.domain.advise_evidence_identity import (
    advise_candidate_source_ref,
    advise_source_evidence_fingerprint,
)


def test_advise_evidence_identity_matches_owner_canonical_source_reference() -> None:
    candidate_id = "candidate-1257"
    content_hash = "sha256:" + ("a" * 64)

    assert advise_candidate_source_ref(
        candidate_id=candidate_id,
        evidence_content_hash=content_hash,
    ) == {
        "source_system": "lotus-idea",
        "source_type": "IdeaCandidate",
        "source_id": candidate_id,
        "content_hash": content_hash,
    }
    assert (
        advise_source_evidence_fingerprint(
            candidate_id=candidate_id,
            evidence_content_hash=content_hash,
        )
        == "sha256:5ebacdf8feb34ea550f86b3b557ec39d28c75647f9257a78d6ebd5617f31f558"
    )


def test_advise_evidence_fingerprint_binds_candidate_and_content() -> None:
    content_hash = "sha256:" + ("a" * 64)

    baseline = advise_source_evidence_fingerprint(
        candidate_id="candidate-1257",
        evidence_content_hash=content_hash,
    )

    assert baseline != content_hash
    assert baseline != advise_source_evidence_fingerprint(
        candidate_id="candidate-other",
        evidence_content_hash=content_hash,
    )
    assert baseline != advise_source_evidence_fingerprint(
        candidate_id="candidate-1257",
        evidence_content_hash="sha256:" + ("b" * 64),
    )
