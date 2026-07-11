from __future__ import annotations

from collections.abc import Mapping
import re


IMAGE_IDENTITY_CONTRACT_VERSION = "lotus.image-identity.v1"
REGISTRY_DIGEST_BINDING = "runtime_release_manifest"

_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_PUBLISHED_PROFILES = frozenset({"demo", "staging", "production"})
_PLACEHOLDERS = frozenset(
    {
        "local",
        "local-unpublished",
        "unknown",
        "registry-digest-resolved-in-release-evidence",
    }
)


def release_identity_metadata(environment: Mapping[str, str]) -> dict[str, object]:
    digest, reference = _validated_digest_pair(environment)
    return {
        "gitCommitSha": _value(environment, "LOTUS_GIT_COMMIT_SHA", "unknown"),
        "gitBranch": _value(environment, "LOTUS_GIT_BRANCH", "unknown"),
        "buildTimestamp": _value(environment, "LOTUS_BUILD_TIMESTAMP", "unknown"),
        "repoUrl": _value(environment, "LOTUS_REPO_URL", "unknown"),
        "ciRunId": _value(environment, "LOTUS_CI_RUN_ID", "local"),
        "imageBuildId": _value(environment, "LOTUS_IMAGE_BUILD_ID", "local"),
        "imageIdentityContractVersion": IMAGE_IDENTITY_CONTRACT_VERSION,
        "registryDigestBinding": REGISTRY_DIGEST_BINDING,
        "imageDigest": digest,
        "imageDigestReference": reference,
        "releaseIdentityStatus": "digest_bound" if digest is not None else "local_unpublished",
    }


def release_identity_configuration_blockers(
    environment: Mapping[str, str],
) -> tuple[str, ...]:
    raw_digest = _optional_value(environment, "LOTUS_RELEASE_IMAGE_DIGEST")
    raw_reference = _optional_value(environment, "LOTUS_RELEASE_IMAGE_DIGEST_REFERENCE")
    blockers: list[str] = []
    if raw_digest is not None and not _valid_digest(raw_digest):
        blockers.append("release_image_digest_invalid")
    if raw_reference is not None and not _valid_reference(raw_reference):
        blockers.append("release_image_digest_reference_invalid")
    if (raw_digest is None) != (raw_reference is None):
        blockers.append("release_image_digest_binding_incomplete")
    if (
        raw_digest is not None
        and raw_reference is not None
        and _valid_digest(raw_digest)
        and _valid_reference(raw_reference)
        and not raw_reference.endswith(f"@{raw_digest}")
    ):
        blockers.append("release_image_digest_binding_mismatch")
    profile = _value(environment, "LOTUS_IDEA_RUNTIME_PROFILE", "local").lower()
    if profile in _PUBLISHED_PROFILES and (raw_digest is None or raw_reference is None):
        blockers.append("release_image_digest_binding_missing")
    return tuple(dict.fromkeys(blockers))


def _validated_digest_pair(environment: Mapping[str, str]) -> tuple[str | None, str | None]:
    if release_identity_configuration_blockers(environment):
        return None, None
    digest = _optional_value(environment, "LOTUS_RELEASE_IMAGE_DIGEST")
    reference = _optional_value(environment, "LOTUS_RELEASE_IMAGE_DIGEST_REFERENCE")
    return digest, reference


def _valid_digest(value: str) -> bool:
    return value not in _PLACEHOLDERS and _DIGEST.fullmatch(value) is not None


def _valid_reference(value: str) -> bool:
    repository, separator, digest = value.rpartition("@")
    return bool(repository and separator and _valid_digest(digest))


def _optional_value(environment: Mapping[str, str], name: str) -> str | None:
    value = environment.get(name, "").strip()
    return value or None


def _value(environment: Mapping[str, str], name: str, default: str) -> str:
    return environment.get(name, default).strip() or default
