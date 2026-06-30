from __future__ import annotations

import re


def _target_block(makefile: str, target: str) -> str:
    pattern = re.compile(rf"^{re.escape(target)}:.*?(?=^\S|\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(makefile)
    return match.group(0) if match else ""


def validate_release_evidence_targets(makefile: str) -> list[str]:
    errors: list[str] = []
    release_sbom = _target_block(makefile, "release-sbom")
    if "-m cyclonedx_py environment" not in release_sbom:
        errors.append("Makefile release-sbom target must run pinned venv `cyclonedx_py`")
    if "--output-file sbom.cdx.json" not in release_sbom:
        errors.append("Makefile release-sbom target must write `sbom.cdx.json`")

    container_scan = _target_block(makefile, "container-image-scan")
    if "$(VENV_PYTHON)" in container_scan:
        errors.append(
            "Makefile container-image-scan target must not require the repository Python venv"
        )
    if "DOCKER_SOCKET_MOUNT := /var/run/docker.sock:/var/run/docker.sock" not in makefile:
        errors.append("Makefile must define the Linux Docker socket mount for image scanning")
    if "DOCKER_SOCKET_MOUNT := //var/run/docker.sock:/var/run/docker.sock" not in makefile:
        errors.append("Makefile must define the Windows Docker Desktop socket mount for scanning")
    if "DOCKER_WORKDIR := /work" not in makefile:
        errors.append("Makefile must define the Linux container scan workdir")
    if "DOCKER_WORKDIR := //work" not in makefile:
        errors.append("Makefile must define the Windows-safe container scan workdir")
    if "TRIVY_IMAGE ?= aquasec/trivy:0.71.2" not in makefile:
        errors.append("Makefile must pin `TRIVY_IMAGE` to `aquasec/trivy:0.71.2`")
    required_fragments = {
        "mkdir -p $(dir $(CONTAINER_SCAN_OUTPUT))": (
            "Makefile container-image-scan target must create the scan evidence directory "
            "without requiring a Python venv"
        ),
        "$(DOCKER_SOCKET_MOUNT)": (
            "Makefile container-image-scan target must use the governed Docker socket mount"
        ),
        "$(DOCKER_WORKDIR)": (
            "Makefile container-image-scan target must use the governed container workdir"
        ),
        "$(TRIVY_IMAGE)": "Makefile container-image-scan target must use pinned Trivy variable",
        "--severity $(CONTAINER_SCAN_SEVERITY)": (
            "Makefile container-image-scan target must use governed severity policy"
        ),
        "--exit-code 1": "Makefile container-image-scan target must fail on governed findings",
        "--ignore-unfixed": "Makefile container-image-scan target must document unfixed-CVE policy",
        "--format json": "Makefile container-image-scan target must write JSON evidence",
        "$(CONTAINER_SCAN_OUTPUT)": (
            "Makefile container-image-scan target must write governed scan evidence"
        ),
        "$(CONTAINER_IMAGE_NAME)": (
            "Makefile container-image-scan target must scan the governed service image"
        ),
    }
    for fragment, error in required_fragments.items():
        if fragment not in container_scan:
            errors.append(error)
    return errors


def validate_dependency_governance(pyproject: str, ci_tooling_lock: str) -> list[str]:
    errors: list[str] = []
    if '"cyclonedx-bom==7.3.0"' not in pyproject:
        errors.append("pyproject.toml dev dependencies must pin `cyclonedx-bom==7.3.0`")
    if "cyclonedx-bom==7.3.0" not in ci_tooling_lock:
        errors.append("requirements/ci-tooling.lock.txt must pin `cyclonedx-bom==7.3.0`")
    return errors
