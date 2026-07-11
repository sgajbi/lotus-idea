from __future__ import annotations

from datetime import datetime
from typing import Callable, Protocol, TypeVar


class Ed25519SignatureReference(Protocol):
    @property
    def algorithm(self) -> str: ...

    @property
    def key_id(self) -> str: ...

    @property
    def rotation_epoch(self) -> int: ...


class Ed25519PublicKeyReference(Protocol):
    @property
    def key_id(self) -> str: ...

    @property
    def algorithm(self) -> str: ...

    @property
    def curve(self) -> str: ...

    @property
    def rotation_epoch(self) -> int: ...

    @property
    def status(self) -> str: ...

    @property
    def not_before_utc(self) -> datetime: ...

    @property
    def not_after_utc(self) -> datetime | None: ...


_PublicKeyT = TypeVar("_PublicKeyT", bound=Ed25519PublicKeyReference)


def select_trusted_ed25519_key(
    *,
    signature: Ed25519SignatureReference,
    keys: tuple[_PublicKeyT, ...],
    issued_at_utc: datetime,
    require: Callable[[bool, str], None],
) -> _PublicKeyT:
    require(signature.algorithm == "EdDSA", "signature algorithm")
    matches = tuple(key for key in keys if key.key_id == signature.key_id)
    require(len(matches) == 1, "known unique signing key")
    key = matches[0]
    require(key.algorithm == "EdDSA" and key.curve == "Ed25519", "signing key algorithm")
    require(key.status in {"active", "rotated"}, "signing key status")
    require(key.rotation_epoch == signature.rotation_epoch, "rotation epoch")
    require(key.not_before_utc <= issued_at_utc, "key validity start")
    require(key.not_after_utc is None or issued_at_utc < key.not_after_utc, "key validity end")
    return key
