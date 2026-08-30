from __future__ import annotations

import pytest

from app.application.persisted_action_evidence import (
    PersistedActionEvidenceUnavailable,
    require_single_persisted_action,
)


def test_require_single_persisted_action_returns_the_only_match() -> None:
    persisted_action = object()

    assert require_single_persisted_action([persisted_action]) is persisted_action


@pytest.mark.parametrize("matches", ([], [object(), object()]))
def test_require_single_persisted_action_rejects_missing_or_ambiguous_matches(
    matches: list[object],
) -> None:
    with pytest.raises(
        PersistedActionEvidenceUnavailable,
        match="exactly one persisted action",
    ):
        require_single_persisted_action(matches)
