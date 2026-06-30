from __future__ import annotations

from typing import Any, Mapping


class InMemoryIdeaLookupMixin:
    _candidate_records: Mapping[str, Any]
    _conversion_intent_candidates: Mapping[str, str]
    _report_evidence_pack_candidates: Mapping[str, str]

    def conversion_intent_by_id(self, conversion_intent_id: str) -> Any | None:
        _require_text(conversion_intent_id, "conversion_intent_id")
        candidate_id = self._conversion_intent_candidates.get(conversion_intent_id)
        record = self._candidate_records.get(candidate_id) if candidate_id is not None else None
        intents = record.conversion_intents if record is not None else ()
        return next(
            (
                intent
                for intent in intents
                if intent.intent.conversion_intent_id == conversion_intent_id
            ),
            None,
        )

    def candidate_record_for_conversion_intent(self, conversion_intent_id: str) -> Any | None:
        _require_text(conversion_intent_id, "conversion_intent_id")
        candidate_id = self._conversion_intent_candidates.get(conversion_intent_id)
        if candidate_id is None:
            return None
        return self._candidate_records.get(candidate_id)

    def report_evidence_pack_by_id(self, report_evidence_pack_id: str) -> Any | None:
        _require_text(report_evidence_pack_id, "report_evidence_pack_id")
        return report_evidence_pack_by_id(
            self._candidate_records,
            self._report_evidence_pack_candidates,
            report_evidence_pack_id,
        )


def report_evidence_pack_by_id(
    candidate_records: Mapping[str, Any],
    report_evidence_pack_candidates: Mapping[str, str],
    report_evidence_pack_id: str,
) -> Any | None:
    candidate_id = report_evidence_pack_candidates.get(report_evidence_pack_id)
    record = candidate_records.get(candidate_id) if candidate_id is not None else None
    packs = record.report_evidence_packs if record is not None else ()
    return next(
        (pack for pack in packs if pack.report_evidence_pack_id == report_evidence_pack_id),
        None,
    )


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
