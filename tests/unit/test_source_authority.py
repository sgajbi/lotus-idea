from pathlib import Path

import pytest

from app.application.source_authority import (
    SourceAuthoritySource,
    build_source_authority_records,
    source_authority_records_are_valid,
    source_authority_records_digest,
)


def test_builds_and_validates_ordered_digest_bound_source_authority(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.py"
    first.write_text('{"contract":"v1"}', encoding="utf-8")
    second.write_text("CONTRACT = 'v1'\n", encoding="utf-8")
    sources = (
        SourceAuthoritySource("lotus-idea", "contracts/first.json", first),
        SourceAuthoritySource("lotus-ai", "../lotus-ai/src/second.py", second),
    )

    records = build_source_authority_records(sources)

    assert tuple(record["repository"] for record in records) == ("lotus-idea", "lotus-ai")
    assert all(len(record["sha256"] or "") == 64 for record in records)
    assert source_authority_records_are_valid(records, expected_sources=sources) is True
    assert len(source_authority_records_digest(records) or "") == 64


def test_missing_source_cannot_form_valid_source_authority(tmp_path: Path) -> None:
    sources = (SourceAuthoritySource("lotus-ai", "src/missing.py", tmp_path / "missing.py"),)

    records = build_source_authority_records(sources)

    assert records[0]["sha256"] is None
    assert source_authority_records_are_valid(records, expected_sources=sources) is False


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("repository", "lotus-risk"),
        ("ref", "src/other.py"),
        ("sha256", "z" * 64),
        ("sha256", "a" * 63),
    ],
)
def test_rejects_source_authority_identity_or_digest_substitution(
    mutation: str,
    value: str,
    tmp_path: Path,
) -> None:
    path = tmp_path / "source.py"
    path.write_text("SOURCE = True\n", encoding="utf-8")
    sources = (SourceAuthoritySource("lotus-idea", "src/source.py", path),)
    records = [dict(record) for record in build_source_authority_records(sources)]
    records[0][mutation] = value

    assert source_authority_records_are_valid(records, expected_sources=sources) is False


def test_rejects_unknown_source_authority_fields(tmp_path: Path) -> None:
    path = tmp_path / "source.py"
    path.write_text("SOURCE = True\n", encoding="utf-8")
    sources = (SourceAuthoritySource("lotus-idea", "src/source.py", path),)
    records = [dict(record) for record in build_source_authority_records(sources)]
    records[0]["runtimeCertified"] = True

    assert source_authority_records_are_valid(records, expected_sources=sources) is False
    assert source_authority_records_digest(records) is None
