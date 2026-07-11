from __future__ import annotations

import pytest

from app.runtime.release_identity import (
    IMAGE_IDENTITY_CONTRACT_VERSION,
    release_identity_configuration_blockers,
    release_identity_metadata,
)


DIGEST = f"sha256:{'a' * 64}"
REFERENCE = f"ghcr.io/sgajbi/lotus-idea@{DIGEST}"


def test_local_identity_is_explicitly_unpublished_without_fake_digest() -> None:
    metadata = release_identity_metadata({})

    assert metadata["imageIdentityContractVersion"] == IMAGE_IDENTITY_CONTRACT_VERSION
    assert metadata["registryDigestBinding"] == "runtime_release_manifest"
    assert metadata["imageDigest"] is None
    assert metadata["imageDigestReference"] is None
    assert metadata["releaseIdentityStatus"] == "local_unpublished"
    assert release_identity_configuration_blockers({}) == ()


def test_published_identity_binds_digest_and_reference() -> None:
    environment = {
        "LOTUS_IDEA_RUNTIME_PROFILE": "production",
        "LOTUS_RELEASE_IMAGE_DIGEST": DIGEST,
        "LOTUS_RELEASE_IMAGE_DIGEST_REFERENCE": REFERENCE,
    }

    assert release_identity_configuration_blockers(environment) == ()
    metadata = release_identity_metadata(environment)
    assert metadata["imageDigest"] == DIGEST
    assert metadata["imageDigestReference"] == REFERENCE
    assert metadata["releaseIdentityStatus"] == "digest_bound"


@pytest.mark.parametrize(
    ("environment", "expected_blocker"),
    [
        (
            {
                "LOTUS_RELEASE_IMAGE_DIGEST": "local-unpublished",
                "LOTUS_RELEASE_IMAGE_DIGEST_REFERENCE": "ghcr.io/example/image@local-unpublished",
            },
            "release_image_digest_invalid",
        ),
        (
            {"LOTUS_RELEASE_IMAGE_DIGEST": DIGEST},
            "release_image_digest_binding_incomplete",
        ),
        (
            {
                "LOTUS_RELEASE_IMAGE_DIGEST": DIGEST,
                "LOTUS_RELEASE_IMAGE_DIGEST_REFERENCE": (
                    f"ghcr.io/sgajbi/lotus-idea@sha256:{'b' * 64}"
                ),
            },
            "release_image_digest_binding_mismatch",
        ),
        (
            {"LOTUS_IDEA_RUNTIME_PROFILE": "staging"},
            "release_image_digest_binding_missing",
        ),
    ],
)
def test_invalid_or_missing_release_binding_fails_closed(
    environment: dict[str, str], expected_blocker: str
) -> None:
    blockers = release_identity_configuration_blockers(environment)

    assert expected_blocker in blockers
    metadata = release_identity_metadata(environment)
    assert metadata["imageDigest"] is None
    assert metadata["imageDigestReference"] is None
    assert metadata["releaseIdentityStatus"] == "local_unpublished"
