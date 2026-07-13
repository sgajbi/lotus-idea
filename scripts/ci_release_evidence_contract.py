from __future__ import annotations

import re


SECRET_LIKE_BUILD_METADATA_NAMES = (
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASSWD",
    "CREDENTIAL",
    "PRIVATE",
    "API_KEY",
    "ACCESS_KEY",
)


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


def _validate_release_identity_target(makefile: str) -> list[str]:
    errors: list[str] = []
    release_identity_gate = _target_block(makefile, "release-image-identity-contract-gate")
    governed_paths = {
        "RELEASE_IMAGE_IDENTITY_MANIFEST ?= release-evidence.json": (
            "Makefile must govern the release identity manifest evidence path"
        ),
        "RELEASE_IMAGE_IDENTITY_LABELS ?= release-image-labels.json": (
            "Makefile must govern the release identity OCI-label evidence path"
        ),
        "RELEASE_IMAGE_IDENTITY_RUNTIME_SMOKE ?= release-runtime-smoke.json": (
            "Makefile must govern the release identity runtime evidence path"
        ),
    }
    for fragment, error in governed_paths.items():
        if fragment not in makefile:
            errors.append(error)
    for fragment in (
        "scripts/release_image_identity_contract.py",
        "--manifest $(RELEASE_IMAGE_IDENTITY_MANIFEST)",
        "--labels $(RELEASE_IMAGE_IDENTITY_LABELS)",
        "--runtime-smoke $(RELEASE_IMAGE_IDENTITY_RUNTIME_SMOKE)",
    ):
        if fragment not in release_identity_gate:
            errors.append(
                f"Makefile release image identity gate missing governed fragment `{fragment}`"
            )
    return errors


def validate_release_evidence_targets(makefile: str) -> list[str]:
    errors: list[str] = []
    if "CONTAINER_BASE_IMAGE ?= python:3.12-slim" not in makefile:
        errors.append("Makefile must govern `CONTAINER_BASE_IMAGE` as `python:3.12-slim`")
    governed_image_tag = (
        "BUILD_IMAGE_TAG ?= $(if $(BUILD_GIT_COMMIT_SHA),$(BUILD_GIT_COMMIT_SHA),local)"
    )
    if governed_image_tag not in makefile:
        errors.append("Makefile must derive the container image tag from the Git commit SHA")
    if "CONTAINER_IMAGE_NAME ?= lotus-idea:$(BUILD_IMAGE_TAG)" not in makefile:
        errors.append("Makefile must tag the governed service image with the Git commit SHA")
    if "docker push" in makefile:
        errors.append("Makefile must not push images; registry publication is CI-only")

    docker_build = _target_block(makefile, "docker-build")
    if "--build-arg PYTHON_BASE_IMAGE=$(CONTAINER_BASE_IMAGE)" not in docker_build:
        errors.append("Makefile docker-build target must pass governed Docker base image")
    for fragment, error in {
        "--build-arg GIT_COMMIT_SHA=$(BUILD_GIT_COMMIT_SHA)": (
            "Makefile docker-build target must pass Git commit SHA provenance"
        ),
        "--build-arg GIT_BRANCH=$(BUILD_GIT_BRANCH)": (
            "Makefile docker-build target must pass Git branch provenance"
        ),
        "--build-arg BUILD_TIMESTAMP=$(BUILD_TIMESTAMP)": (
            "Makefile docker-build target must pass build timestamp provenance"
        ),
        "--build-arg REPO_URL=$(BUILD_REPO_URL)": (
            "Makefile docker-build target must pass repository URL provenance"
        ),
        "--build-arg CI_RUN_ID=$(BUILD_CI_RUN_ID)": (
            "Makefile docker-build target must pass CI run ID provenance"
        ),
        "--build-arg IMAGE_BUILD_ID=$(BUILD_IMAGE_BUILD_ID)": (
            "Makefile docker-build target must pass non-self-referential image build identity"
        ),
        "--build-arg SERVICE_VERSION=$(BUILD_SERVICE_VERSION)": (
            "Makefile docker-build target must pass service version provenance"
        ),
    }.items():
        if fragment not in docker_build:
            errors.append(error)

    errors.extend(_validate_container_runtime_smoke_target(makefile))

    errors.extend(_validate_release_identity_target(makefile))

    release_sbom = _target_block(makefile, "release-sbom")
    if "-m cyclonedx_py requirements" not in release_sbom:
        errors.append(
            "Makefile release-sbom target must run pinned venv `cyclonedx_py requirements`"
        )
    if "-m cyclonedx_py environment" in release_sbom:
        errors.append(
            "Makefile release-sbom target must not generate an ambiguous environment SBOM"
        )
    if "requirements/runtime-resolved.lock.txt" not in release_sbom:
        errors.append(
            "Makefile release-sbom target must use the resolved runtime dependency lockfile"
        )
    if "requirements/shared-runtime.lock.txt" in release_sbom:
        errors.append(
            "Makefile release-sbom target must not use the direct-only shared runtime lockfile"
        )
    if "--pyproject pyproject.toml" not in release_sbom:
        errors.append("Makefile release-sbom target must attach project metadata")
    if "--output-reproducible" not in release_sbom:
        errors.append("Makefile release-sbom target must generate reproducible SBOM output")
    if "--output-file sbom.cdx.json" not in release_sbom:
        errors.append("Makefile release-sbom target must write `sbom.cdx.json`")
    if "scripts/finalize_release_sbom.py sbom.cdx.json" not in release_sbom:
        errors.append(
            "Makefile release-sbom target must finalize CycloneDX JSON for GitHub SBOM attestation"
        )

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


def validate_compose_runtime_contract(compose: str) -> list[str]:
    required = {
        'GIT_COMMIT_SHA: "${LOTUS_IDEA_BUILD_GIT_COMMIT_SHA:-unknown}"': "commit SHA",
        'GIT_BRANCH: "${LOTUS_IDEA_BUILD_GIT_BRANCH:-unknown}"': "Git branch",
        'BUILD_TIMESTAMP: "${LOTUS_IDEA_BUILD_TIMESTAMP:-unknown}"': "build timestamp",
        'REPO_URL: "${LOTUS_IDEA_BUILD_REPO_URL:-https://github.com/sgajbi/lotus-idea.git}"': (
            "repository URL"
        ),
        'CI_RUN_ID: "${LOTUS_IDEA_BUILD_RUN_ID:-local}"': "run ID",
        'IMAGE_BUILD_ID: "${LOTUS_IDEA_BUILD_IMAGE_ID:-local}"': "image build ID",
        'SERVICE_VERSION: "${LOTUS_IDEA_BUILD_SERVICE_VERSION:-0.1.0}"': "service version",
    }
    errors = [
        f"docker-compose.yml must pass governed {label} build identity"
        for fragment, label in required.items()
        if fragment not in compose
    ]
    required_realization = {
        "      LOTUS_IDEA_ADVISE_REALIZATION_BASE_URL:": "Advise realization base URL",
        "      LOTUS_IDEA_ADVISE_REALIZATION_SUBMIT_PATH:": "Advise realization submit path",
        "      LOTUS_IDEA_MANAGE_REALIZATION_BASE_URL:": "Manage realization base URL",
        "      LOTUS_IDEA_MANAGE_REALIZATION_SUBMIT_PATH:": "Manage realization submit path",
        "      LOTUS_IDEA_REPORT_REALIZATION_BASE_URL:": "Report realization base URL",
        "      LOTUS_IDEA_REPORT_REALIZATION_SUBMIT_PATH:": "Report realization submit path",
    }
    errors.extend(
        f"docker-compose.yml must configure governed {label}"
        for fragment, label in required_realization.items()
        if fragment not in compose
    )
    required_persistence = {
        "  lotus-idea-postgres:": "a dedicated PostgreSQL service",
        "    image: postgres:18-alpine": "the governed PostgreSQL image",
        "      - lotus-idea-postgres-data:/var/lib/postgresql\n": (
            "a PostgreSQL 18-compatible durable volume"
        ),
        "  lotus-idea-migrations:": "a separate migration runner",
        '    command: ["python", "scripts/run_migrations.py", "--direction", "apply"]': (
            "the app-owned migration command"
        ),
        "        condition: service_completed_successfully": (
            "migration completion before application startup"
        ),
        '  LOTUS_IDEA_RUNTIME_PROFILE: "${LOTUS_IDEA_RUNTIME_PROFILE:-local}"': (
            "an explicit standalone runtime profile"
        ),
        '  LOTUS_IDEA_DATABASE_URL: "${LOTUS_IDEA_DATABASE_URL:-postgresql://': (
            "the PostgreSQL repository URL"
        ),
    }
    errors.extend(
        f"docker-compose.yml must configure {label}"
        for fragment, label in required_persistence.items()
        if fragment not in compose
    )
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
        'org.opencontainers.image.version="${SERVICE_VERSION}"': (
            "Dockerfile must label the service version"
        ),
        'org.opencontainers.image.revision="${GIT_COMMIT_SHA}"': (
            "Dockerfile must label the Git commit SHA"
        ),
        'io.lotus.image.git.branch="${GIT_BRANCH}"': "Dockerfile must label the Git branch",
        'org.opencontainers.image.created="${BUILD_TIMESTAMP}"': (
            "Dockerfile must label the build timestamp"
        ),
        'org.opencontainers.image.source="${REPO_URL}"': "Dockerfile must label the repo URL",
        'io.lotus.image.ci.run_id="${CI_RUN_ID}"': "Dockerfile must label the CI run ID",
        'io.lotus.image.build.id="${IMAGE_BUILD_ID}"': (
            "Dockerfile must label the non-self-referential image build identity"
        ),
        'io.lotus.image.identity.contract="lotus.image-identity.v1"': (
            "Dockerfile must label the image identity contract"
        ),
        'io.lotus.image.registry.digest.binding="runtime-release-manifest"': (
            "Dockerfile must label the registry digest binding authority"
        ),
        'LOTUS_GIT_COMMIT_SHA="${GIT_COMMIT_SHA}"': (
            "Dockerfile must expose Git commit SHA to runtime metadata"
        ),
        'LOTUS_GIT_BRANCH="${GIT_BRANCH}"': (
            "Dockerfile must expose Git branch to runtime metadata"
        ),
        'LOTUS_BUILD_TIMESTAMP="${BUILD_TIMESTAMP}"': (
            "Dockerfile must expose build timestamp to runtime metadata"
        ),
        'LOTUS_REPO_URL="${REPO_URL}"': "Dockerfile must expose repo URL to runtime metadata",
        'LOTUS_CI_RUN_ID="${CI_RUN_ID}"': ("Dockerfile must expose CI run ID to runtime metadata"),
        'LOTUS_IMAGE_BUILD_ID="${IMAGE_BUILD_ID}"': (
            "Dockerfile must expose image build identity to runtime metadata"
        ),
        'LOTUS_SERVICE_VERSION="${SERVICE_VERSION}"': (
            "Dockerfile must expose service version to runtime metadata"
        ),
        "COPY requirements/runtime-resolved.lock.txt ./requirements/runtime-resolved.lock.txt": (
            "Dockerfile must copy the resolved runtime dependency lockfile"
        ),
        "COPY pyproject.toml README.md LICENSE THIRD_PARTY_NOTICES.md ./": (
            "Dockerfile must include service license and third-party notices"
        ),
        (
            "python -m pip install --no-cache-dir --requirement "
            "requirements/runtime-resolved.lock.txt"
        ): ("Dockerfile must install the resolved runtime dependency lockfile before source copy"),
        "python -m pip install --no-cache-dir --no-deps .": (
            "Dockerfile must install the local service package without reinstalling dependencies"
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
        "COPY scripts/run_migrations.py ./scripts/run_migrations.py": (
            "Dockerfile must include the standalone migration entrypoint"
        ),
    }
    for fragment, error in required_fragments.items():
        if fragment not in dockerfile:
            errors.append(error)
    errors.extend(_validate_prohibited_dockerfile_fragments(dockerfile))
    for line_number, line in enumerate(dockerfile.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for name_match in re.findall(
            r"(?:ARG|ENV)\s+([A-Za-z_][A-Za-z0-9_]*)|\b([A-Za-z_][A-Za-z0-9_]*)=",
            stripped,
        ):
            variable_name = next(part for part in name_match if part)
            if any(marker in variable_name.upper() for marker in SECRET_LIKE_BUILD_METADATA_NAMES):
                errors.append(
                    f"Dockerfile line {line_number} must not expose secret-like build "
                    f"metadata variable `{variable_name}` through ARG/ENV"
                )
    ordered_fragments = [
        "COPY requirements/runtime-resolved.lock.txt ./requirements/runtime-resolved.lock.txt",
        "python -m pip install --no-cache-dir --requirement requirements/runtime-resolved.lock.txt",
        "COPY src ./src",
        "python -m pip install --no-cache-dir --no-deps .",
    ]
    positions = [dockerfile.find(fragment) for fragment in ordered_fragments]
    if all(position >= 0 for position in positions) and positions != sorted(positions):
        errors.append(
            "Dockerfile must install resolved runtime dependencies before copying source and "
            "installing the local package"
        )
    return errors


def _validate_prohibited_dockerfile_fragments(dockerfile: str) -> list[str]:
    prohibited_fragments = {
        "ARG IMAGE_DIGEST": (
            "Dockerfile must not accept a self-referential registry digest build argument"
        ),
        "io.lotus.image.digest=": (
            "Dockerfile must not claim a pre-publication value is the registry digest"
        ),
        "LOTUS_IMAGE_DIGEST=": (
            "Dockerfile must not bake a registry digest placeholder into runtime metadata"
        ),
        'pip install --no-cache-dir -e ".[dev]"': (
            "Dockerfile runtime image must not install development extras"
        ),
        'pip install --no-cache-dir ".[dev]"': (
            "Dockerfile runtime image must not install development extras"
        ),
        "COPY scripts ./scripts": "Dockerfile runtime image must not copy CI/developer scripts",
        "USER root": "Dockerfile runtime image must not run as root",
    }
    return [error for fragment, error in prohibited_fragments.items() if fragment in dockerfile]


def validate_dependency_governance(pyproject: str, ci_tooling_lock: str) -> list[str]:
    errors: list[str] = []
    if '"cyclonedx-bom==7.3.0"' not in pyproject:
        errors.append("pyproject.toml dev dependencies must pin `cyclonedx-bom==7.3.0`")
    if "cyclonedx-bom==7.3.0" not in ci_tooling_lock:
        errors.append("requirements/ci-tooling.lock.txt must pin `cyclonedx-bom==7.3.0`")
    return errors
