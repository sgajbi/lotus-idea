from __future__ import annotations

from argparse import Namespace
from datetime import UTC, datetime
import json
from pathlib import Path

import pytest
from pytest import CaptureFixture

from scripts.proof_generator_io import (
    core_control_plane_base_url_from_args,
    core_query_base_url_from_args,
    parse_generated_at_utc,
    required_base_url_from_args,
    timeout_seconds_from_args,
    write_json_payload,
)


def test_parse_generated_at_utc_accepts_zulu_timestamp() -> None:
    assert parse_generated_at_utc("2026-06-21T10:10:00Z") == datetime(
        2026, 6, 21, 10, 10, tzinfo=UTC
    )


def test_parse_generated_at_utc_normalizes_offset_timestamp() -> None:
    assert parse_generated_at_utc("2026-06-21T18:10:00+08:00") == datetime(
        2026, 6, 21, 10, 10, tzinfo=UTC
    )


def test_parse_generated_at_utc_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="generated-at-utc must be timezone-aware"):
        parse_generated_at_utc("2026-06-21T10:10:00")


def test_timeout_seconds_from_args_parses_positive_numeric_text() -> None:
    assert timeout_seconds_from_args(Namespace(timeout_seconds="2.5")) == 2.5


def test_timeout_seconds_from_args_rejects_non_numeric_text() -> None:
    with pytest.raises(ValueError, match="timeout seconds must be numeric"):
        timeout_seconds_from_args(Namespace(timeout_seconds="fast"))


def test_timeout_seconds_from_args_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError, match="timeout seconds must be positive"):
        timeout_seconds_from_args(Namespace(timeout_seconds="0"))


def test_required_base_url_from_args_prefers_primary_value() -> None:
    assert (
        required_base_url_from_args(
            Namespace(primary_url=" https://core-query.example ", fallback_url="https://core"),
            primary_attr="primary_url",
            fallback_attr="fallback_url",
            primary_option="--primary-url",
            fallback_option="--fallback-url",
            primary_env="PRIMARY_URL",
            fallback_env="FALLBACK_URL",
        )
        == "https://core-query.example"
    )


def test_required_base_url_from_args_uses_fallback_value() -> None:
    assert (
        required_base_url_from_args(
            Namespace(primary_url=None, fallback_url=" https://core.example "),
            primary_attr="primary_url",
            fallback_attr="fallback_url",
            primary_option="--primary-url",
            fallback_option="--fallback-url",
            primary_env="PRIMARY_URL",
            fallback_env="FALLBACK_URL",
        )
        == "https://core.example"
    )


def test_required_base_url_from_args_rejects_absent_values() -> None:
    with pytest.raises(
        ValueError,
        match="--primary-url, --fallback-url, PRIMARY_URL, or FALLBACK_URL is required",
    ):
        required_base_url_from_args(
            Namespace(primary_url=" ", fallback_url=None),
            primary_attr="primary_url",
            fallback_attr="fallback_url",
            primary_option="--primary-url",
            fallback_option="--fallback-url",
            primary_env="PRIMARY_URL",
            fallback_env="FALLBACK_URL",
        )


def test_core_control_plane_base_url_from_args_uses_control_plane_before_base() -> None:
    assert (
        core_control_plane_base_url_from_args(
            Namespace(
                core_query_control_plane_base_url=" https://core-control.example ",
                core_base_url="https://core.example",
            ),
            control_plane_env="LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL",
            base_env="LOTUS_CORE_BASE_URL",
        )
        == "https://core-control.example"
    )


def test_core_query_base_url_from_args_uses_core_query_before_base() -> None:
    assert (
        core_query_base_url_from_args(
            Namespace(
                core_query_base_url=" https://core-query.example ",
                core_base_url="https://core.example",
            ),
            query_env="LOTUS_CORE_QUERY_BASE_URL",
            base_env="LOTUS_CORE_BASE_URL",
        )
        == "https://core-query.example"
    )


def test_write_json_payload_writes_sorted_indented_file(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "proof.json"

    write_json_payload({"z": 1, "a": {"b": True}}, output=str(output_path))

    assert output_path.read_text(encoding="utf-8") == (
        '{\n  "a": {\n    "b": true\n  },\n  "z": 1\n}\n'
    )


def test_write_json_payload_binds_aggregate_provenance_for_generated_proofs(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output" / "opportunity" / "proof.json"

    write_json_payload(
        {
            "schemaVersion": "test-proof.v1",
            "generatedAtUtc": "2026-06-21T10:10:00Z",
        },
        output=str(output_path),
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    provenance = payload["aggregateProofProvenance"]
    assert provenance["repository"] == "lotus-idea"
    assert provenance["proofRef"].endswith("output/opportunity/proof.json")
    assert provenance["proofGeneratedAtUtc"] == "2026-06-21T10:10:00Z"
    assert len(provenance["artifactSha256"]) == 64
    assert isinstance(provenance["sourceTreeDirty"], bool)


def test_write_json_payload_prints_when_output_is_absent(
    capsys: CaptureFixture[str],
) -> None:
    write_json_payload({"z": 1, "a": 2}, output=None)

    assert capsys.readouterr().out == '{\n  "a": 2,\n  "z": 1\n}\n'
