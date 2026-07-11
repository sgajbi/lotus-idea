from __future__ import annotations

from copy import deepcopy

from scripts.release_image_identity_contract import validate_release_image_identity


DIGEST = f"sha256:{'a' * 64}"
REFERENCE = f"ghcr.io/sgajbi/lotus-idea@{DIGEST}"


def evidence() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    manifest: dict[str, object] = {
        "commit_sha": "commit-001",
        "branch": "main",
        "build_timestamp": "2026-07-11T08:00:00Z",
        "repository_url": "https://github.com/sgajbi/lotus-idea",
        "run_id": "1234",
        "image_build_id": "commit-001.1234",
        "container_image_repository": "ghcr.io/sgajbi/lotus-idea",
        "container_image_digest": DIGEST,
        "container_image_digest_reference": REFERENCE,
        "kubernetes_deployment_reference": REFERENCE,
        "image_signature": {"subject": REFERENCE},
        "provenance_attestation": {"subject": REFERENCE},
        "sbom_attestation": {"subject": REFERENCE},
    }
    labels: dict[str, object] = {
        "org.opencontainers.image.revision": "commit-001",
        "io.lotus.image.git.branch": "main",
        "org.opencontainers.image.created": "2026-07-11T08:00:00Z",
        "org.opencontainers.image.source": "https://github.com/sgajbi/lotus-idea",
        "io.lotus.image.ci.run_id": "1234",
        "io.lotus.image.build.id": "commit-001.1234",
        "io.lotus.image.identity.contract": "lotus.image-identity.v1",
        "io.lotus.image.registry.digest.binding": "runtime-release-manifest",
    }
    runtime = {
        "containerRuntimeSmoke": [
            {
                "path": "/version",
                "statusCode": 200,
                "payload": {
                    "build": {
                        "gitCommitSha": "commit-001",
                        "gitBranch": "main",
                        "buildTimestamp": "2026-07-11T08:00:00Z",
                        "repoUrl": "https://github.com/sgajbi/lotus-idea",
                        "ciRunId": "1234",
                        "imageBuildId": "commit-001.1234",
                        "imageIdentityContractVersion": "lotus.image-identity.v1",
                        "registryDigestBinding": "runtime_release_manifest",
                        "imageDigest": DIGEST,
                        "imageDigestReference": REFERENCE,
                        "releaseIdentityStatus": "digest_bound",
                    }
                },
            }
        ]
    }
    return manifest, labels, runtime


def test_release_identity_contract_accepts_one_cross_bound_artifact() -> None:
    manifest, labels, runtime = evidence()

    assert validate_release_image_identity(manifest, labels, runtime) == []


def test_release_identity_contract_rejects_digest_subject_and_runtime_drift() -> None:
    manifest, labels, runtime = evidence()
    degraded_manifest = deepcopy(manifest)
    degraded_labels = deepcopy(labels)
    degraded_runtime = deepcopy(runtime)
    degraded_manifest["kubernetes_deployment_reference"] = "mutable:latest"
    degraded_manifest["image_signature"] = {"subject": f"sha256:{'b' * 64}"}
    degraded_labels["io.lotus.image.digest"] = "registry-digest-resolved-in-release-evidence"
    probes = degraded_runtime["containerRuntimeSmoke"]
    assert isinstance(probes, list)
    payload = probes[0]["payload"]
    assert isinstance(payload, dict)
    build = payload["build"]
    assert isinstance(build, dict)
    build["imageDigest"] = f"sha256:{'c' * 64}"

    errors = validate_release_image_identity(
        degraded_manifest,
        degraded_labels,
        degraded_runtime,
    )

    assert "kubernetes_deployment_reference must match the release digest reference" in errors
    assert "image_signature_subject must match the release digest reference" in errors
    assert "OCI labels must not claim the self-referential registry digest" in errors
    assert "runtime /version imageDigest must match release identity" in errors
    assert "published release identity must not contain placeholder metadata" in errors
