"""The digest rule is anchored to the producer, not restated beside it (#1282).

Nine modules each held a private copy of `^sha256:[0-9a-f]{64}$`. A tenth copy
in a shared module would only have moved the duplication, so the rule earns its
place by being checked against what the producers actually emit: if
`evidence_hashing` ever changes format, `test_the_rule_matches_what_the_producer_emits`
fails rather than the two drifting apart silently.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.evidence_digest import (
    LEGACY_REVISION_VECTOR_SENTINEL,
    is_sha256_digest,
    require_revision_vector_digest,
    require_sha256_digest,
)
from app.domain.evidence_hashing import evidence_hash_for_source_refs
from app.domain.ideas import EvidenceFreshness, SourceRef, SourceSystem


def _source_ref(*, product_id: str = "product-a") -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/portfolio-state",
        as_of_date=datetime(2026, 8, 30, tzinfo=UTC).date(),
        generated_at_utc=datetime(2026, 8, 30, 12, tzinfo=UTC),
        content_hash=f"sha256:{'a' * 64}",
        data_quality_status="clean",
        freshness=EvidenceFreshness.CURRENT,
    )


def test_the_rule_matches_what_the_producer_emits() -> None:
    """The anchor. Without this the pattern is a convention someone typed."""

    produced = evidence_hash_for_source_refs((_source_ref(),))

    assert produced.startswith("sha256:")
    assert is_sha256_digest(produced), produced
    require_sha256_digest(produced, "evidence_content_hash")


def test_two_different_inputs_produce_two_valid_and_different_digests() -> None:
    """Guards against a rule satisfied by a constant.

    A validator that accepted one fixed string would pass the test above.
    """

    first = evidence_hash_for_source_refs((_source_ref(product_id="product-a"),))
    second = evidence_hash_for_source_refs((_source_ref(product_id="product-b"),))

    assert first != second
    assert is_sha256_digest(first) and is_sha256_digest(second)


@pytest.mark.parametrize(
    "value",
    [
        "sha256:evidence",
        "sha256:",
        "sha256:" + "a" * 63,
        "sha256:" + "a" * 65,
        "sha256:" + "A" * 64,
        "sha1:" + "a" * 64,
        "a" * 64,
        "",
        "   ",
        None,
        123,
    ],
)
def test_malformed_digests_are_refused(value: object) -> None:
    assert not is_sha256_digest(value)
    with pytest.raises(ValueError, match="sha256:<64 lowercase hex>"):
        require_sha256_digest(value, "evidence_content_hash")


def test_uppercase_hex_is_refused_so_one_digest_has_one_spelling() -> None:
    """Two spellings of the same digest would compare unequal as strings.

    Called out separately from the parametrized cases because it is the one
    rejection a reader is most likely to think is an oversight.
    """

    assert not is_sha256_digest("sha256:" + "A" * 64)
    assert is_sha256_digest("sha256:" + "a" * 64)


def test_the_refusal_names_the_shape_rather_than_reporting_a_missing_field() -> None:
    """`sha256:evidence` is present; it is the wrong shape, and that is a
    different repair from supplying a value that is absent."""

    with pytest.raises(ValueError) as refusal:
        require_sha256_digest("sha256:evidence", "evidence_content_hash")

    message = str(refusal.value)
    assert "evidence_content_hash" in message
    assert "sha256:<64 lowercase hex>" in message
    assert "sha256:evidence" in message
    assert "is required" not in message


def test_the_legacy_revision_sentinel_is_admitted_only_by_the_revision_rule() -> None:
    """Rows persisted before `source_revision_vector_digest` existed decode to
    this sentinel in four places in `postgres_codecs`. Enforcing the digest
    shape on that field would be a read outage on historical data, not a
    validation tightening - so the two rules are deliberately different, and
    that difference is asserted here rather than left as a comment.
    """

    require_revision_vector_digest(LEGACY_REVISION_VECTOR_SENTINEL, "source_revision_vector_digest")

    with pytest.raises(ValueError, match="sha256:<64 lowercase hex>"):
        require_sha256_digest(LEGACY_REVISION_VECTOR_SENTINEL, "source_revision_vector_digest")


def test_the_revision_rule_still_refuses_everything_else() -> None:
    """The sentinel is one admitted value, not an open door."""

    require_revision_vector_digest(f"sha256:{'b' * 64}", "source_revision_vector_digest")

    for value in ("legacy:other", "legacy:", "unknown", "sha256:nope", ""):
        with pytest.raises(ValueError):
            require_revision_vector_digest(value, "source_revision_vector_digest")
