from __future__ import annotations

import json
import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.application.downstream_realization.advise_intake_runtime_execution import (  # noqa: E402
    ADVISE_INTAKE_RUNTIME_EXECUTION_ENV,
    advise_intake_runtime_execution_is_valid,
)


def main(argv: list[str] | None = None) -> int:
    path_value = (argv or sys.argv[1:] or [os.getenv(ADVISE_INTAKE_RUNTIME_EXECUTION_ENV)])[0]
    if path_value is None:
        print(
            f"usage: {Path(__file__).name} <proof-json-path>; "
            f"or set {ADVISE_INTAKE_RUNTIME_EXECUTION_ENV}",
            file=sys.stderr,
        )
        return 2
    path = Path(path_value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        print("Advise intake runtime proof must be a JSON object", file=sys.stderr)
        return 1
    if not advise_intake_runtime_execution_is_valid(payload):
        print("Advise intake runtime proof is invalid", file=sys.stderr)
        return 1
    print(f"Advise intake runtime proof valid: {path.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
