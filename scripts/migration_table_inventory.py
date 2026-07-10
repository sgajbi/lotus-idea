from __future__ import annotations

from pathlib import Path
import re

CREATE_TABLE_PATTERN = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(idea_[a-z0-9_]+)", re.IGNORECASE
)


def migration_owned_tables(
    repository_root: Path, migrations_path: Path = Path("migrations")
) -> set[str]:
    tables: set[str] = set()
    for migration in sorted((repository_root / migrations_path).glob("*.sql")):
        if migration.name.endswith(".rollback.sql"):
            continue
        tables.update(CREATE_TABLE_PATTERN.findall(migration.read_text(encoding="utf-8")))
    return tables
