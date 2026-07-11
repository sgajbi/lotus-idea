from __future__ import annotations


def lifecycle_authority_decision_payload() -> dict[str, object]:
    return {
        "claims": {
            "schema_version": "lotus.lifecycle-authority-decision.v1",
            "issuer": "bank-lifecycle-governance",
            "audience": "lotus-idea",
            "decision_id": "privacy-decision-001",
            "replay_nonce": "a" * 64,
            "tenant_id": "tenant-private-bank-sg",
            "candidate_id": "candidate-expired-001",
            "action": "purge",
            "authority_domain": "privacy",
            "authority_ref": "bank-privacy-governance:decision-001",
            "change_reference": "privacy-case-001",
            "decision_status": "approved",
            "issued_at_utc": "2026-07-12T05:58:00Z",
            "effective_at_utc": "2026-07-12T05:59:00Z",
            "expires_at_utc": "2026-07-12T06:05:00Z",
        },
        "signature": {
            "algorithm": "EdDSA",
            "key_id": "lifecycle-key-001",
            "rotation_epoch": 3,
            "signature_base64url": "c2lnbmF0dXJl",
        },
        "key_discovery_path": "/.well-known/lotus-lifecycle-authority-keys",
    }


def lifecycle_authority_key_payload() -> dict[str, object]:
    return {
        "schema_version": "lotus.lifecycle-authority-keys.v1",
        "issuer": "bank-lifecycle-governance",
        "keys": [
            {
                "key_id": "lifecycle-key-001",
                "algorithm": "EdDSA",
                "curve": "Ed25519",
                "public_key_base64url": "cHVibGljLWtleQ",
                "rotation_epoch": 3,
                "status": "active",
                "not_before_utc": "2026-07-01T00:00:00Z",
                "not_after_utc": None,
            }
        ],
    }
