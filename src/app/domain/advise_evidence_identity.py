from __future__ import annotations

import hashlib
import json


def advise_candidate_source_ref(
    *,
    candidate_id: str,
    evidence_content_hash: str,
) -> dict[str, str]:
    return {
        "source_system": "lotus-idea",
        "source_type": "IdeaCandidate",
        "source_id": candidate_id,
        "content_hash": evidence_content_hash,
    }


def advise_source_evidence_fingerprint(
    *,
    candidate_id: str,
    evidence_content_hash: str,
) -> str:
    source_ref = advise_candidate_source_ref(
        candidate_id=candidate_id,
        evidence_content_hash=evidence_content_hash,
    )
    canonical = json.dumps([source_ref], sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
