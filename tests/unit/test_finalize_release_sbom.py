from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.finalize_release_sbom import finalize_cyclonedx_sbom, finalize_release_sbom


def test_finalize_cyclonedx_sbom_adds_deterministic_attestation_serial() -> None:
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "components": [{"name": "fastapi", "version": "0.138.2", "type": "library"}],
    }

    finalized = finalize_cyclonedx_sbom(sbom)
    rerun = finalize_cyclonedx_sbom(dict(sbom))

    assert finalized["serialNumber"].startswith("urn:uuid:")
    assert finalized["serialNumber"] == rerun["serialNumber"]
    assert sbom.get("serialNumber") is None


def test_finalize_release_sbom_preserves_existing_content(tmp_path: Path) -> None:
    path = tmp_path / "sbom.cdx.json"
    path.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "version": 1,
                "components": [{"name": "uvicorn", "version": "0.49.0", "type": "library"}],
            }
        ),
        encoding="utf-8",
    )

    finalize_release_sbom(path)

    finalized = json.loads(path.read_text(encoding="utf-8"))
    assert finalized["bomFormat"] == "CycloneDX"
    assert finalized["specVersion"] == "1.6"
    assert finalized["components"][0]["name"] == "uvicorn"
    assert finalized["serialNumber"].startswith("urn:uuid:")


def test_finalize_release_sbom_rejects_non_cyclonedx_json() -> None:
    with pytest.raises(ValueError, match="CycloneDX JSON"):
        finalize_cyclonedx_sbom({"spdxVersion": "SPDX-2.3", "SPDXID": "SPDXRef-DOCUMENT"})
