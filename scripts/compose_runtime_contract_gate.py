from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[1]
SHARED_IMAGE = "lotus-idea:local"
MIGRATION_SERVICE = "lotus-idea-migrations"
API_SERVICE = "lotus-idea"
WORKER_SERVICE = "lotus-idea-source-ingestion-worker"


def validate_compose_model(
    model: Mapping[str, Any],
    *,
    include_worker: bool,
) -> list[str]:
    services = model.get("services")
    if not isinstance(services, Mapping):
        return ["normalized Compose model must define a services object"]

    consumers = [MIGRATION_SERVICE, API_SERVICE]
    if include_worker:
        consumers.append(WORKER_SERVICE)
    missing = [name for name in consumers if not isinstance(services.get(name), Mapping)]
    if missing:
        return [f"normalized Compose model is missing required service(s): {sorted(missing)}"]

    errors: list[str] = []
    shared_image_services = sorted(
        name
        for name, service in services.items()
        if isinstance(name, str)
        and isinstance(service, Mapping)
        and service.get("image") == SHARED_IMAGE
    )
    if shared_image_services != sorted(consumers):
        errors.append(
            "normalized Compose model must bind the shared lotus-idea:local image only "
            f"to {sorted(consumers)}; found {shared_image_services}"
        )

    build_owners = sorted(
        name
        for name, service in services.items()
        if isinstance(name, str)
        and isinstance(service, Mapping)
        and service.get("image") == SHARED_IMAGE
        and "build" in service
    )
    if build_owners != [MIGRATION_SERVICE]:
        errors.append(
            "normalized Compose model must define lotus-idea-migrations as the only "
            f"lotus-idea:local build owner; found {build_owners}"
        )

    for consumer in consumers[1:]:
        service = cast(Mapping[str, Any], services[consumer])
        depends_on = service.get("depends_on")
        if not isinstance(depends_on, Mapping) or MIGRATION_SERVICE not in depends_on:
            errors.append(
                f"normalized Compose service {consumer} must depend on "
                f"{MIGRATION_SERVICE} before consuming the shared image"
            )
    return errors


def _normalized_compose_model(*, include_worker: bool) -> tuple[dict[str, Any] | None, list[str]]:
    command = ["docker", "compose"]
    if include_worker:
        command.extend(("--profile", "worker"))
    command.extend(("config", "--format", "json"))
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    profile = "worker" if include_worker else "base"
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown Compose error"
        return None, [f"{profile} Compose normalization failed: {detail}"]
    try:
        model = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return None, [f"{profile} Compose normalization returned invalid JSON: {exc}"]
    if not isinstance(model, dict):
        return None, [f"{profile} Compose normalization must return a JSON object"]
    return model, []


def main() -> int:
    errors: list[str] = []
    for include_worker in (False, True):
        model, load_errors = _normalized_compose_model(include_worker=include_worker)
        errors.extend(load_errors)
        if model is not None:
            errors.extend(validate_compose_model(model, include_worker=include_worker))
    if errors:
        print("Compose runtime contract failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Compose runtime contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
