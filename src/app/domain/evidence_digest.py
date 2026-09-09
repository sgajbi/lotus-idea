"""The shape of an evidence digest, in one place (#1282).

Nine modules each compiled their own copy of `^sha256:[0-9a-f]{64}$` and four
evidence fields checked only that they were non-empty after strip, so the
repository enforced two different standards on the same kind of value and the
weaker one sat on the boundary `lotus-render` consumes. Adding a tenth copy
would have been the finding restated.

This module deliberately imports nothing from the domain. The validator is
needed by `ideas.SourceRef` and `ideas.LineageRef`, while the producer
(`evidence_hashing`) imports `ideas` - so a validator living beside the
producer would be a cycle.

The pattern is not a convention restated by hand: `test_evidence_digest.py`
asserts the producer's own output satisfies it, so the two cannot drift
without a test failing.
"""

from __future__ import annotations

import re

# `hexdigest()` is 64 lowercase hex characters, so the producers satisfy this
# by construction. Anchored, and lowercase-only: accepting uppercase would let
# two spellings of one digest compare unequal as strings.
_SHA256_DIGEST_BODY = r"sha256:[0-9a-f]{64}"
SHA256_DIGEST_PATTERN = re.compile(rf"^{_SHA256_DIGEST_BODY}$")

# Rows persisted before `source_revision_vector_digest` existed decode to this
# in `postgres_codecs`, in four places. It is a statement that no revision
# vector is known, not a digest, and it must keep loading - enforcing the
# digest shape on that field would be a read outage on historical data rather
# than a validation tightening.
LEGACY_REVISION_VECTOR_SENTINEL = "legacy:unknown"
REVISION_VECTOR_DIGEST_PATTERN = re.compile(
    rf"^(?:{_SHA256_DIGEST_BODY}|{re.escape(LEGACY_REVISION_VECTOR_SENTINEL)})$"
)


def is_sha256_digest(value: object) -> bool:
    """True when `value` is a well-formed `sha256:<64 lowercase hex>` digest."""

    return isinstance(value, str) and SHA256_DIGEST_PATTERN.fullmatch(value) is not None


def require_sha256_digest(value: object, field_name: str) -> None:
    """Refuse anything that is not a well-formed digest, naming the cause.

    Distinct from the emptiness error these fields used to raise: an operator
    who sends `sha256:evidence` is told the shape is wrong rather than that a
    required field is missing, which is a different repair.
    """

    if not is_sha256_digest(value):
        raise ValueError(f"{field_name} must be a sha256:<64 lowercase hex> digest, got {value!r}")


def require_revision_vector_digest(value: object, field_name: str) -> None:
    """As above, but the legacy sentinel is a valid value for this field.

    Kept as its own function rather than a flag on the one above, so the
    exclusion is visible at every call site instead of being a boolean an
    author has to notice.
    """

    if not isinstance(value, str) or REVISION_VECTOR_DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(
            f"{field_name} must be a sha256:<64 lowercase hex> digest "
            f"or {LEGACY_REVISION_VECTOR_SENTINEL!r}, got {value!r}"
        )
