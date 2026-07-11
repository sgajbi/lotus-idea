from __future__ import annotations

import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class Ed25519SignatureVerifier:
    def verify(
        self,
        *,
        public_key_base64url: str,
        signature_base64url: str,
        canonical_payload: bytes,
    ) -> None:
        try:
            Ed25519PublicKey.from_public_bytes(_decode(public_key_base64url)).verify(
                _decode(signature_base64url), canonical_payload
            )
        except (InvalidSignature, ValueError) as exc:
            raise ValueError("Ed25519 signature is invalid") from exc


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
