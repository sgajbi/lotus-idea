from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def non_authority_claims_are_valid(
    claims: Mapping[str, Any],
    *,
    owners: Mapping[str, str],
) -> bool:
    return all(claims.get(key) == value for key, value in owners.items()) and all(
        value is False for key, value in claims.items() if key not in owners
    )
