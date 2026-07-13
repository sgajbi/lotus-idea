from __future__ import annotations

from typing import Protocol

from app.domain.deployment_migrations import (
    DeploymentMigrationCommand,
    DeploymentMigrationResult,
)


class DeploymentMigrationExecutor(Protocol):
    def execute(self, command: DeploymentMigrationCommand) -> DeploymentMigrationResult: ...
