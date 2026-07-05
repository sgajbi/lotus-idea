from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any


_SERIAL_NAMESPACE = uuid.UUID("f5d0e2d3-49c6-4e42-a68f-b197e31f5e21")


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def finalize_cyclonedx_sbom(sbom: dict[str, Any]) -> dict[str, Any]:
    if sbom.get("bomFormat") != "CycloneDX" or "specVersion" not in sbom:
        raise ValueError("release SBOM must be CycloneDX JSON with a specVersion")

    normalized = dict(sbom)
    normalized.pop("serialNumber", None)
    serial = uuid.uuid5(_SERIAL_NAMESPACE, _stable_json(normalized))
    finalized = dict(sbom)
    finalized["serialNumber"] = f"urn:uuid:{serial}"
    return finalized


def finalize_release_sbom(path: Path) -> None:
    sbom = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(sbom, dict):
        raise ValueError("release SBOM root must be a JSON object")
    finalized = finalize_cyclonedx_sbom(sbom)
    path.write_text(json.dumps(finalized, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: finalize_release_sbom.py <sbom.cdx.json>", file=sys.stderr)
        return 2
    finalize_release_sbom(Path(args[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
