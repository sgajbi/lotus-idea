from __future__ import annotations

from scripts.ci_main_releasability_permission_contract import (
    validate_main_releasability_permissions,
)


def test_write_permission_is_confined_to_reclamation_job() -> None:
    workflow = """
permissions:
  contents: read
jobs:
  validate:
    permissions:
      contents: write

  reclaim-dispatch-tag:
    permissions:
      contents: write
"""

    errors = validate_main_releasability_permissions("main-releasability.yml", workflow)

    assert errors == ["main-releasability.yml must keep contents:write outside validation jobs"]


def test_reclamation_job_requires_exactly_one_write_grant() -> None:
    workflow = """
permissions:
  contents: read
jobs:
  validate:
    runs-on: ubuntu-latest

  reclaim-dispatch-tag:
    permissions:
      contents: read
"""

    errors = validate_main_releasability_permissions("main-releasability.yml", workflow)

    assert errors == [
        "main-releasability.yml must grant contents:write exactly once in the reclamation job"
    ]


def test_other_workflows_are_out_of_scope() -> None:
    assert validate_main_releasability_permissions("feature-lane.yml", "") == []
