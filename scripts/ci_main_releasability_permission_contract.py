from __future__ import annotations


def validate_main_releasability_permissions(workflow_name: str, workflow: str) -> list[str]:
    """Keep write authority confined to the dispatch-tag reclamation job."""
    if workflow_name != "main-releasability.yml":
        return []

    marker = "\n  reclaim-dispatch-tag:\n"
    if workflow.count(marker) != 1:
        return ["main-releasability.yml must define exactly one final reclaim-dispatch-tag job"]

    validation_workflow, reclamation_job = workflow.split(marker, maxsplit=1)
    errors: list[str] = []
    if "contents: write" in validation_workflow:
        errors.append("main-releasability.yml must keep contents:write outside validation jobs")
    if reclamation_job.count("contents: write") != 1:
        errors.append(
            "main-releasability.yml must grant contents:write exactly once in the reclamation job"
        )
    return errors
