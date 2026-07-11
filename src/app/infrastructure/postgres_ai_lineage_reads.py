from __future__ import annotations

from typing import Any

from app.domain.ai_lineage_persistence import AIExplanationLineageRecord
from app.infrastructure.postgres_codecs import (
    ai_explanation_lineage_from_json,
    read_json_object,
    read_row_value,
)


def ai_explanation_lineage_from_row(row: Any) -> AIExplanationLineageRecord:
    return ai_explanation_lineage_from_json(
        read_json_object(row, "lineage_json"),
        expected_integrity_version=read_row_value(row, "output_integrity_version"),
        expected_content_digest=read_row_value(row, "output_content_digest"),
    )
