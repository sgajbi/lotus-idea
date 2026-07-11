from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


SHA256_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
IDENTITY_CONTRACT = "lotus.image-identity.v1"
REGISTRY_DIGEST_BINDING_LABEL = "runtime-release-manifest"
PLACEHOLDERS = {
    "local",
    "local-unpublished",
    "unknown",
    "registry-digest-resolved-in-release-evidence",
}


def validate_release_image_identity(
    manifest: dict[str, Any],
    labels: dict[str, Any],
    runtime_smoke: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    digest = manifest.get("container_image_digest")
    digest_reference = manifest.get("container_image_digest_reference")
    repository = manifest.get("container_image_repository")
    if not isinstance(digest, str) or SHA256_DIGEST.fullmatch(digest) is None:
        errors.append("release manifest container image digest must be a sha256 digest")
    if digest_reference != f"{repository}@{digest}":
        errors.append("release manifest digest reference must bind repository and digest")
    for field in (
        "kubernetes_deployment_reference",
        "image_signature_subject",
        "provenance_attestation_subject",
        "sbom_attestation_subject",
    ):
        observed = _manifest_subject(manifest, field)
        if observed != digest_reference:
            errors.append(f"{field} must match the release digest reference")

    expected_labels = {
        "org.opencontainers.image.revision": manifest.get("commit_sha"),
        "io.lotus.image.git.branch": manifest.get("branch"),
        "org.opencontainers.image.created": manifest.get("build_timestamp"),
        "org.opencontainers.image.source": manifest.get("repository_url"),
        "io.lotus.image.ci.run_id": str(manifest.get("run_id")),
        "io.lotus.image.build.id": manifest.get("image_build_id"),
        "io.lotus.image.identity.contract": IDENTITY_CONTRACT,
        "io.lotus.image.registry.digest.binding": REGISTRY_DIGEST_BINDING_LABEL,
    }
    for key, expected in expected_labels.items():
        if labels.get(key) != expected:
            errors.append(f"OCI label {key} must match release manifest build identity")
    if "io.lotus.image.digest" in labels:
        errors.append("OCI labels must not claim the self-referential registry digest")

    build = _runtime_build(runtime_smoke)
    runtime_expected = {
        "gitCommitSha": manifest.get("commit_sha"),
        "gitBranch": manifest.get("branch"),
        "buildTimestamp": manifest.get("build_timestamp"),
        "repoUrl": manifest.get("repository_url"),
        "ciRunId": str(manifest.get("run_id")),
        "imageBuildId": manifest.get("image_build_id"),
        "imageIdentityContractVersion": IDENTITY_CONTRACT,
        "registryDigestBinding": "runtime_release_manifest",
        "imageDigest": digest,
        "imageDigestReference": digest_reference,
        "releaseIdentityStatus": "digest_bound",
    }
    if not isinstance(build, dict):
        errors.append("release runtime smoke must include /version build metadata")
    else:
        for key, expected in runtime_expected.items():
            if build.get(key) != expected:
                errors.append(f"runtime /version {key} must match release identity")

    if (
        _contains_placeholder(manifest)
        or _contains_placeholder(labels)
        or _contains_placeholder(runtime_smoke)
    ):
        errors.append("published release identity must not contain placeholder metadata")
    return errors


def _manifest_subject(manifest: dict[str, Any], field: str) -> object:
    if field == "kubernetes_deployment_reference":
        return manifest.get(field)
    section_name = field.removesuffix("_subject")
    section = manifest.get(section_name)
    return section.get("subject") if isinstance(section, dict) else None


def _runtime_build(runtime_smoke: dict[str, Any]) -> object:
    probes = runtime_smoke.get("containerRuntimeSmoke")
    if not isinstance(probes, list):
        return None
    for probe in probes:
        if isinstance(probe, dict) and probe.get("path") == "/version":
            payload = probe.get("payload")
            return payload.get("build") if isinstance(payload, dict) else None
    return None


def _contains_placeholder(value: object) -> bool:
    if isinstance(value, str):
        return value in PLACEHOLDERS
    if isinstance(value, dict):
        return any(_contains_placeholder(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_placeholder(item) for item in value)
    return False


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate published image identity evidence.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--runtime-smoke", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_release_image_identity(
        _load_object(args.manifest),
        _load_object(args.labels),
        _load_object(args.runtime_smoke),
    )
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Release image identity contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
