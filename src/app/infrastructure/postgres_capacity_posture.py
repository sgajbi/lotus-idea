from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.domain.capacity_posture import (
    PostgresCapacityPosture,
    evaluate_postgres_capacity_posture,
)
from app.infrastructure.postgres_protocols import PostgresConnection


POSTGRES_CAPACITY_POSTURE_QUERY = """
/* lotus-idea postgres-capacity-posture */
SELECT COUNT(*)::double precision /
       current_setting('max_connections')::double precision
       AS connection_utilization_fraction
FROM pg_stat_activity
"""


def load_postgres_capacity_posture(
    connection: PostgresConnection,
) -> PostgresCapacityPosture:
    try:
        with connection.cursor() as cursor:
            cursor.execute(POSTGRES_CAPACITY_POSTURE_QUERY)
            rows = cursor.fetchall()
    except Exception:
        return evaluate_postgres_capacity_posture(None)
    row = rows[0] if len(rows) == 1 else None
    return evaluate_postgres_capacity_posture(_utilization_fraction(row))


def _utilization_fraction(row: Any) -> float | None:
    raw_measurement: object
    if isinstance(row, Mapping):
        raw_measurement = row.get("connection_utilization_fraction")
    elif isinstance(row, Sequence) and not isinstance(row, (str, bytes)) and len(row) == 1:
        raw_measurement = row[0]
    else:
        return None
    if isinstance(raw_measurement, bool) or not isinstance(raw_measurement, (int, float)):
        return None
    measurement = float(raw_measurement)
    return measurement if 0 <= measurement <= 1 else None
