from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.proof_artifact_files import read_optional_json_object


def test_read_optional_json_object_returns_none_without_path() -> None:
    assert read_optional_json_object(None, artifact_name="proof") is None


def test_read_optional_json_object_loads_object(tmp_path: Path) -> None:
    path = tmp_path / "proof.json"
    path.write_text('{"status": "ready"}', encoding="utf-8")

    assert read_optional_json_object(path, artifact_name="proof") == {"status": "ready"}


def test_read_optional_json_object_rejects_non_object_payload(tmp_path: Path) -> None:
    path = tmp_path / "proof.json"
    path.write_text('["not", "object"]', encoding="utf-8")

    with pytest.raises(ValueError, match="proof must be a JSON object"):
        read_optional_json_object(path, artifact_name="proof")
