from __future__ import annotations

import re


def _target_block(makefile: str, target: str) -> str:
    pattern = re.compile(rf"^{re.escape(target)}:.*?(?=^\S|\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(makefile)
    return match.group(0) if match else ""


def _validate_container_runtime_smoke_target(makefile: str) -> list[str]:
    errors: list[str] = []
    container_runtime_smoke = _target_block(makefile, "container-runtime-smoke")
    governed_smoke_variables = {
        "CONTAINER_SMOKE_NAME ?= lotus-idea-runtime-smoke": (
            "Makefile must govern the container runtime smoke container name"
        ),
        "CONTAINER_SMOKE_HOST ?= 127.0.0.1": (
            "Makefile must govern the container runtime smoke host binding"
        ),
        "CONTAINER_SMOKE_HOST_PORT ?= 18330": (
            "Makefile must govern the container runtime smoke host port"
        ),
        "CONTAINER_SMOKE_CONTAINER_PORT ?= 8330": (
            "Makefile must govern the container runtime smoke container port"
        ),
        "CONTAINER_SMOKE_TIMEOUT_SECONDS ?= 45": (
            "Makefile must govern the container runtime smoke startup timeout"
        ),
        "CONTAINER_SMOKE_PROBE_INTERVAL_SECONDS ?= 1": (
            "Makefile must govern the container runtime smoke probe interval"
        ),
    }
    for fragment, error in governed_smoke_variables.items():
        if fragment not in makefile:
            errors.append(error)
    required_smoke_fragments = {
        "python scripts/container_runtime_smoke.py": (
            "Makefile container-runtime-smoke target must use the governed smoke script"
        ),
        "--image-name $(CONTAINER_IMAGE_NAME)": (
            "Makefile container-runtime-smoke target must test the governed service image"
        ),
        "--container-name $(CONTAINER_SMOKE_NAME)": (
            "Makefile container-runtime-smoke target must use the governed container name"
        ),
        "--host $(CONTAINER_SMOKE_HOST)": (
            "Makefile container-runtime-smoke target must use the governed host"
        ),
        "--host-port $(CONTAINER_SMOKE_HOST_PORT)": (
            "Makefile container-runtime-smoke target must use the governed host port"
        ),
        "--container-port $(CONTAINER_SMOKE_CONTAINER_PORT)": (
            "Makefile container-runtime-smoke target must use the governed container port"
        ),
        "--startup-timeout-seconds $(CONTAINER_SMOKE_TIMEOUT_SECONDS)": (
            "Makefile container-runtime-smoke target must use the governed startup timeout"
        ),
        "--probe-interval-seconds $(CONTAINER_SMOKE_PROBE_INTERVAL_SECONDS)": (
            "Makefile container-runtime-smoke target must use the governed probe interval"
        ),
    }
    for fragment, error in required_smoke_fragments.items():
        if fragment not in container_runtime_smoke:
            errors.append(error)
    return errors


def validate_release_evidence_targets(makefile: str) -> list[str]:
    errors: list[str] = []
    if "CONTAINER_BASE_IMAGE ?= python:3.12-slim" not in makefile:
        errors.append("Makefile must govern `CONTAINER_BASE_IMAGE` as `python:3.12-slim`")

    docker_build = _target_block(makefile, "docker-build")
    if "--build-arg PYTHON_BASE_IMAGE=$(CONTAINER_BASE_IMAGE)" not in docker_build:
        errors.append("Makefile docker-build target must pass governed Docker base image")

    errors.extend(_validate_container_runtime_smoke_target(makefile))

    release_sbom = _target_block(makefile, "release-sbom")
    if "-m cyclonedx_py requirements" not in release_sbom:
        errors.append(
            "Makefile release-sbom target must run pinned venv `cyclonedx_py requirements`"
        )
    if "-m cyclonedx_py environment" in release_sbom:
        errors.append(
            "Makefile release-sbom target must not generate an ambiguous environment SBOM"
        )
    if "requirements/shared-runtime.lock.txt" not in release_sbom:
        errors.append("Makefile release-sbom target must use the shared runtime lockfile")
    if "--pyproject pyproject.toml" not in release_sbom:
        errors.append("Makefile release-sbom target must attach project metadata")
    if "--output-reproducible" not in release_sbom:
        errors.append("Makefile release-sbom target must generate reproducible SBOM output")
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
        errors.append("Makefile must govern `TRIVY_IMAGE` as `aquasec/trivy:0.71.2`")
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


def validate_dockerfile_runtime(dockerfile: str) -> list[str]:
    errors: list[str] = []
    required_fragments = {
        "ARG PYTHON_BASE_IMAGE=python:3.12-slim": (
            "Dockerfile must declare the governed default Python base image"
        ),
        "FROM ${PYTHON_BASE_IMAGE}": "Dockerfile must build from the governed base-image arg",
        'org.opencontainers.image.base.name="${PYTHON_BASE_IMAGE}"': (
            "Dockerfile must label the runtime base image"
        ),
        "python -m pip install --no-cache-dir .": (
            "Dockerfile must install only runtime project dependencies"
        ),
        "USER lotus": "Dockerfile must run the service as the non-root `lotus` user",
        "PYTHONPATH=/app/src": (
            "Dockerfile must keep repository-root runtime contracts resolvable from /app"
        ),
        "COPY scripts/run_source_ingestion_worker.py ./scripts/run_source_ingestion_worker.py": (
            "Dockerfile must keep the runtime run-once worker entrypoint available"
        ),
        (
            "COPY scripts/run_scheduled_source_ingestion_worker.py "
            "./scripts/run_scheduled_source_ingestion_worker.py"
        ): "Dockerfile must keep the runtime scheduled-worker entrypoint available",
    }
    for fragment, error in required_fragments.items():
        if fragment not in dockerfile:
            errors.append(error)
    prohibited_fragments = {
        'pip install --no-cache-dir -e ".[dev]"': (
            "Dockerfile runtime image must not install development extras"
        ),
        'pip install --no-cache-dir ".[dev]"': (
            "Dockerfile runtime image must not install development extras"
        ),
        "COPY scripts ./scripts": "Dockerfile runtime image must not copy CI/developer scripts",
        "USER root": "Dockerfile runtime image must not run as root",
    }
    for fragment, error in prohibited_fragments.items():
        if fragment in dockerfile:
            errors.append(error)
    return errors


def validate_dependency_governance(pyproject: str, ci_tooling_lock: str) -> list[str]:
    errors: list[str] = []
    if '"cyclonedx-bom==7.3.0"' not in pyproject:
        errors.append("pyproject.toml dev dependencies must pin `cyclonedx-bom==7.3.0`")
    if "cyclonedx-bom==7.3.0" not in ci_tooling_lock:
        errors.append("requirements/ci-tooling.lock.txt must pin `cyclonedx-bom==7.3.0`")
    return errors
