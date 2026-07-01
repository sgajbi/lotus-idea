from __future__ import annotations

from typing import Any


def persistence_summary_payload(result: Any) -> dict[str, Any]:
    record = result.record
    audit_event = result.audit_event or (
        record.audit_events[-1] if record is not None and record.audit_events else None
    )
    return {
        "decision": result.decision,
        "candidateId": record.candidate.candidate_id if record is not None else None,
        "lifecycleStatus": record.candidate.lifecycle_status.value if record is not None else None,
        "reviewPosture": record.candidate.review_posture.value if record is not None else None,
        "auditEventType": audit_event.event_type if audit_event is not None else None,
    }
