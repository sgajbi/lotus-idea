from __future__ import annotations

from typing import Any

from scripts.compose_runtime_contract_gate import validate_compose_model


def _normalized_model(*, include_worker: bool = True) -> dict[str, Any]:
    services: dict[str, Any] = {
        "lotus-idea-postgres": {"image": "postgres:18-alpine"},
        "lotus-idea-migrations": {
            "image": "lotus-idea:local",
            "build": {"context": ".", "dockerfile": "Dockerfile"},
            "depends_on": {"lotus-idea-postgres": {"condition": "service_healthy"}},
        },
        "lotus-idea": {
            "image": "lotus-idea:local",
            "environment": {
                "LOTUS_IDEA_ADVISE_REALIZATION_HISTORY_PATH_TEMPLATE": (
                    "/advisory/proposals/idea-intake/{intake_id}/realization"
                ),
                "LOTUS_IDEA_ADVISE_REALIZATION_RECOVERY_HISTORY_PATH": (
                    "/advisory/proposals/idea-intake/realization"
                ),
                "LOTUS_IDEA_ADVISE_REALIZATION_CAPABILITIES": (
                    "advisory.idea_proposal_intake.accept,advisory.idea_proposal_realization.read"
                ),
            },
            "depends_on": {
                "lotus-idea-migrations": {"condition": "service_completed_successfully"}
            },
        },
    }
    if include_worker:
        services["lotus-idea-source-ingestion-worker"] = {
            "image": "lotus-idea:local",
            "depends_on": {
                "lotus-idea-migrations": {"condition": "service_completed_successfully"}
            },
        }
    return {"services": services}


def test_normalized_compose_contract_accepts_base_and_worker_models() -> None:
    assert (
        validate_compose_model(_normalized_model(include_worker=False), include_worker=False) == []
    )
    assert validate_compose_model(_normalized_model(), include_worker=True) == []


def test_normalized_compose_contract_rejects_duplicate_shared_image_builders() -> None:
    model = _normalized_model()
    model["services"]["lotus-idea"]["build"] = {"context": "."}

    assert (
        "normalized Compose model must define lotus-idea-migrations as the only "
        "lotus-idea:local build owner; found ['lotus-idea', 'lotus-idea-migrations']"
        in validate_compose_model(model, include_worker=True)
    )


def test_normalized_compose_contract_rejects_missing_build_owner() -> None:
    model = _normalized_model()
    del model["services"]["lotus-idea-migrations"]["build"]

    assert (
        "normalized Compose model must define lotus-idea-migrations as the only "
        "lotus-idea:local build owner; found []"
        in validate_compose_model(model, include_worker=True)
    )


def test_normalized_compose_contract_rejects_divergent_consumer_image() -> None:
    model = _normalized_model()
    model["services"]["lotus-idea-source-ingestion-worker"]["image"] = "lotus-idea:other"

    assert any(
        "must bind the shared lotus-idea:local image" in error
        for error in validate_compose_model(model, include_worker=True)
    )


def test_normalized_compose_contract_requires_migration_dependency() -> None:
    model = _normalized_model()
    model["services"]["lotus-idea"]["depends_on"] = {}

    assert (
        "normalized Compose service lotus-idea must depend on lotus-idea-migrations "
        "before consuming the shared image" in validate_compose_model(model, include_worker=True)
    )


def test_normalized_compose_contract_requires_advise_history_configuration() -> None:
    model = _normalized_model()
    del model["services"]["lotus-idea"]["environment"][
        "LOTUS_IDEA_ADVISE_REALIZATION_HISTORY_PATH_TEMPLATE"
    ]

    errors = validate_compose_model(model, include_worker=True)

    assert any("canonical Advise realization history path" in error for error in errors)


def test_normalized_compose_contract_requires_advise_history_capability() -> None:
    model = _normalized_model()
    model["services"]["lotus-idea"]["environment"]["LOTUS_IDEA_ADVISE_REALIZATION_CAPABILITIES"] = (
        "advisory.idea_proposal_intake.accept"
    )

    errors = validate_compose_model(model, include_worker=True)

    assert any("intake and realization-read capabilities" in error for error in errors)


def test_normalized_compose_contract_requires_advise_recovery_history_configuration() -> None:
    model = _normalized_model()
    del model["services"]["lotus-idea"]["environment"][
        "LOTUS_IDEA_ADVISE_REALIZATION_RECOVERY_HISTORY_PATH"
    ]

    errors = validate_compose_model(model, include_worker=True)

    assert any("lost-response recovery history path" in error for error in errors)
