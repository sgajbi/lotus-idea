from __future__ import annotations

import hashlib
import json

from app.domain.ideas import IdeaCandidate, SourceRef


def evidence_hash_for_candidate(candidate: IdeaCandidate) -> str:
    return evidence_hash_for_source_refs(candidate.evidence_packet.source_refs)


def evidence_hash_for_source_refs(source_refs: tuple[SourceRef, ...]) -> str:
    payload = [
        {
            "content_hash": source_ref.content_hash,
            "data_quality_status": source_ref.data_quality_status,
            "freshness": source_ref.freshness.value,
            "product_id": source_ref.product_id,
            "product_version": source_ref.product_version,
            "source_system": source_ref.source_system.value,
        }
        for source_ref in sorted(source_refs, key=lambda ref: ref.product_id)
    ]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
