from datetime import UTC, datetime

from app.domain.data_lifecycle import DataLifecycleAction
from app.domain.lifecycle_authority import LifecycleAuthorityDomain
from app.integration.lifecycle_authority_contract import (
    map_lifecycle_authority_decision,
    map_lifecycle_authority_key_discovery,
)
from tests.support.lifecycle_authority_fixture import (
    lifecycle_authority_decision_payload,
    lifecycle_authority_key_payload,
)


def test_maps_exact_lifecycle_authority_decision_and_canonical_claims() -> None:
    envelope = map_lifecycle_authority_decision(lifecycle_authority_decision_payload())

    assert envelope.claims.action is DataLifecycleAction.PURGE
    assert envelope.claims.authority_domain is LifecycleAuthorityDomain.PRIVACY
    assert envelope.claims.issued_at_utc == datetime(2026, 7, 12, 5, 58, tzinfo=UTC)
    assert envelope.canonical_claims["issued_at_utc"] == "2026-07-12T05:58:00Z"
    assert envelope.signature.key_id == "lifecycle-key-001"


def test_maps_lifecycle_authority_key_discovery() -> None:
    discovery = map_lifecycle_authority_key_discovery(lifecycle_authority_key_payload())

    assert discovery.issuer == "bank-lifecycle-governance"
    assert discovery.keys[0].key_id == "lifecycle-key-001"
    assert discovery.keys[0].not_before_utc == datetime(2026, 7, 1, tzinfo=UTC)
