from __future__ import annotations

import hashlib

from app.domain import CandidateChangeReason, CandidateIdentity


def initial_candidate_identity(candidate_id: str) -> CandidateIdentity:
    fingerprint = hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()
    return CandidateIdentity(
        business_identity_id=f"opportunity_fixture_{candidate_id}",
        policy_version="idea-opportunity-identity-v2",
        material_fingerprint=f"sha256:{fingerprint}",
        material_version=1,
        evidence_version=1,
        change_reason=CandidateChangeReason.INITIAL_DETECTION,
    )


__all__ = ["initial_candidate_identity"]
