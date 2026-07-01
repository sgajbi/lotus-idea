from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
from pytest import CaptureFixture

from scripts.proof_generator_io import timeout_seconds_from_args, write_json_payload


def test_timeout_seconds_from_args_parses_positive_numeric_text() -> None:
    assert timeout_seconds_from_args(Namespace(timeout_seconds="2.5")) == 2.5


def test_timeout_seconds_from_args_rejects_non_numeric_text() -> None:
    with pytest.raises(ValueError, match="timeout seconds must be numeric"):
        timeout_seconds_from_args(Namespace(timeout_seconds="fast"))


def test_timeout_seconds_from_args_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError, match="timeout seconds must be positive"):
        timeout_seconds_from_args(Namespace(timeout_seconds="0"))


def test_write_json_payload_writes_sorted_indented_file(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "proof.json"

    write_json_payload({"z": 1, "a": {"b": True}}, output=str(output_path))

    assert output_path.read_text(encoding="utf-8") == (
        '{\n  "a": {\n    "b": true\n  },\n  "z": 1\n}\n'
    )


def test_write_json_payload_prints_when_output_is_absent(
    capsys: CaptureFixture[str],
) -> None:
    write_json_payload({"z": 1, "a": 2}, output=None)

    assert capsys.readouterr().out == '{\n  "a": 2,\n  "z": 1\n}\n'
