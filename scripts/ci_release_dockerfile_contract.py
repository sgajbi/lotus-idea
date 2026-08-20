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

GOVERNED_DOCKERFILE_BASE_AND_METADATA_FRAGMENTS = {
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
    'LOTUS_GIT_BRANCH="${GIT_BRANCH}"': ("Dockerfile must expose Git branch to runtime metadata"),
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
}

GOVERNED_DOCKERFILE_DEPENDENCY_FRAGMENTS = {
    "apt-get upgrade --yes --no-install-recommends": (
        "Dockerfile must apply patched operating-system packages before runtime dependencies"
    ),
    "rm -rf /var/lib/apt/lists/*": (
        "Dockerfile must remove apt package lists after operating-system package refresh"
    ),
    "COPY requirements/runtime-resolved.lock.txt ./requirements/runtime-resolved.lock.txt": (
        "Dockerfile must copy the resolved runtime dependency lockfile"
    ),
    "COPY pyproject.toml README.md LICENSE THIRD_PARTY_NOTICES.md ./": (
        "Dockerfile must include service license and third-party notices"
    ),
    ("python -m pip install --no-cache-dir --requirement requirements/runtime-resolved.lock.txt"): (
        "Dockerfile must install the resolved runtime dependency lockfile before source copy"
    ),
    "python -m pip install --no-cache-dir --no-deps .": (
        "Dockerfile must install the local service package without reinstalling dependencies"
    ),
}

GOVERNED_DOCKERFILE_RUNTIME_FRAGMENTS = {
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
    "COPY scripts/__init__.py ./scripts/__init__.py": (
        "Dockerfile must include the runtime scripts package marker"
    ),
    (
        "COPY scripts/proof_worktree_import_guard.py ./scripts/proof_worktree_import_guard.py"
    ): "Dockerfile must include the runtime proof import guard",
}

GOVERNED_DOCKERFILE_INSTALL_ORDER_FRAGMENTS = (
    "COPY requirements/runtime-resolved.lock.txt ./requirements/runtime-resolved.lock.txt",
    "python -m pip install --no-cache-dir --requirement requirements/runtime-resolved.lock.txt",
    "COPY src ./src",
    "python -m pip install --no-cache-dir --no-deps .",
)


def validate_dockerfile_runtime(dockerfile: str) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_required_dockerfile_fragments(dockerfile))
    errors.extend(_validate_prohibited_dockerfile_fragments(dockerfile))
    errors.extend(_validate_secret_safe_dockerfile_build_metadata(dockerfile))
    errors.extend(_validate_runtime_dependency_install_order(dockerfile))
    return errors


def _validate_required_dockerfile_fragments(dockerfile: str) -> list[str]:
    required_fragments = {
        **GOVERNED_DOCKERFILE_BASE_AND_METADATA_FRAGMENTS,
        **GOVERNED_DOCKERFILE_DEPENDENCY_FRAGMENTS,
        **GOVERNED_DOCKERFILE_RUNTIME_FRAGMENTS,
    }
    return [error for fragment, error in required_fragments.items() if fragment not in dockerfile]


def _validate_secret_safe_dockerfile_build_metadata(dockerfile: str) -> list[str]:
    errors: list[str] = []
    for line_number, line in enumerate(dockerfile.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        errors.extend(_secret_like_build_metadata_errors(line_number, stripped))
    return errors


def _secret_like_build_metadata_errors(line_number: int, stripped_line: str) -> list[str]:
    errors: list[str] = []
    for name_match in re.findall(
        r"(?:ARG|ENV)\s+([A-Za-z_][A-Za-z0-9_]*)|\b([A-Za-z_][A-Za-z0-9_]*)=",
        stripped_line,
    ):
        variable_name = next(part for part in name_match if part)
        if any(marker in variable_name.upper() for marker in SECRET_LIKE_BUILD_METADATA_NAMES):
            errors.append(
                f"Dockerfile line {line_number} must not expose secret-like build "
                f"metadata variable `{variable_name}` through ARG/ENV"
            )
    return errors


def _validate_runtime_dependency_install_order(dockerfile: str) -> list[str]:
    positions = [
        dockerfile.find(fragment) for fragment in GOVERNED_DOCKERFILE_INSTALL_ORDER_FRAGMENTS
    ]
    if all(position >= 0 for position in positions) and positions != sorted(positions):
        return [
            "Dockerfile must install resolved runtime dependencies before copying source and "
            "installing the local package"
        ]
    return []


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
