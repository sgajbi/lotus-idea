from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any


def main() -> int:
    advise_root = Path(os.environ["LOTUS_ADVISE_ROOT"]).resolve()
    sys.path.insert(0, str(advise_root))

    from fastapi.testclient import TestClient
    from src.api.main import app  # type: ignore[import-not-found]

    request = _request_from_stdin()
    with TestClient(app) as client:
        response = client.request(
            request["method"],
            request["path"],
            json=request.get("json"),
            params=request.get("params"),
            headers=request.get("headers"),
        )
    print(json.dumps({"statusCode": response.status_code, "body": response.json()}, sort_keys=True))
    return 0


def _request_from_stdin() -> dict[str, Any]:
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise ValueError("owner bridge request must be an object")
    method = value.get("method")
    path = value.get("path")
    if method not in {"GET", "POST"}:
        raise ValueError("owner bridge method must be GET or POST")
    if not isinstance(path, str) or not path.startswith("/advisory/proposals/idea-intake"):
        raise ValueError("owner bridge path must target the governed Idea intake routes")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
