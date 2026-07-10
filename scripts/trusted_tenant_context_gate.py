from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ACCESS_SCOPE_MODULE = Path("src/app/application/access_scope.py")
CORE_PORT_MODULE = Path("src/app/ports/core_sources.py")
CORE_ADAPTER_MODULE = Path("src/app/infrastructure/lotus_core_sources.py")
SOURCE_INGESTION_MODULE = Path("src/app/application/source_ingestion.py")
SIGNAL_API_SUPPORT_MODULE = Path("src/app/api/signal_api_support.py")
API_BASE_MODEL_MODULE = Path("src/app/api/base_model.py")
OBSERVABILITY_MODULE = Path("src/app/observability/logging.py")

CORE_APPLICATION_MODULES = (
    Path("src/app/application/high_cash_signal.py"),
    Path("src/app/application/low_income_signal.py"),
    Path("src/app/application/bond_maturity_signal.py"),
    Path("src/app/application/missing_benchmark_signal.py"),
)
CORE_API_MODULES = (
    Path("src/app/api/idea_signals.py"),
    Path("src/app/api/low_income_signals.py"),
    Path("src/app/api/bond_maturity_signals.py"),
    Path("src/app/api/missing_benchmark_signals.py"),
)
REQUIRED_TEST_MODULES = (
    Path("tests/unit/test_high_cash_application.py"),
    Path("tests/unit/test_low_income_application.py"),
    Path("tests/unit/test_bond_maturity_application.py"),
    Path("tests/unit/test_missing_benchmark_application.py"),
    Path("tests/unit/test_source_ingestion.py"),
    Path("tests/unit/test_lotus_core_sources.py"),
    Path("tests/integration/test_high_cash_signal_api.py"),
)
REQUIRED_FILES = (
    ACCESS_SCOPE_MODULE,
    CORE_PORT_MODULE,
    CORE_ADAPTER_MODULE,
    SOURCE_INGESTION_MODULE,
    SIGNAL_API_SUPPORT_MODULE,
    API_BASE_MODEL_MODULE,
    OBSERVABILITY_MODULE,
    *CORE_APPLICATION_MODULES,
    *CORE_API_MODULES,
    *REQUIRED_TEST_MODULES,
)


def validate_trusted_tenant_context(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    texts = _read_required_files(root, errors)
    if errors:
        return sorted(errors)

    _require_fragments(
        errors,
        ACCESS_SCOPE_MODULE,
        texts[ACCESS_SCOPE_MODULE],
        ("def tenant_portfolio_scope", "tenant_id=tenant_id", '"tenant_id is required"'),
    )
    _require_fragments(
        errors,
        CORE_PORT_MODULE,
        texts[CORE_PORT_MODULE],
        (
            "tenant_id: str",
            "_validate_core_request_scope",
            'raise ValueError("tenant_id is required")',
        ),
    )

    adapter_text = texts[CORE_ADAPTER_MODULE]
    if '"tenant_id": "default"' in adapter_text:
        errors.append(
            f"{CORE_ADAPTER_MODULE.as_posix()}: hard-coded production tenant fallback is forbidden"
        )
    if adapter_text.count('"tenant_id": request.tenant_id') != 2:
        errors.append(
            f"{CORE_ADAPTER_MODULE.as_posix()}: both tenant-aware Core snapshot payloads must use the request tenant"
        )

    for relative_path in CORE_APPLICATION_MODULES:
        text = texts[relative_path]
        _require_fragments(
            errors,
            relative_path,
            text,
            ("tenant_portfolio_scope", "tenant_id=command."),
        )
        if "portfolio_only_scope(" in text:
            errors.append(
                f"{relative_path.as_posix()}: Core-backed candidate scope must not discard tenant context"
            )

    _require_fragments(
        errors,
        SOURCE_INGESTION_MODULE,
        texts[SOURCE_INGESTION_MODULE],
        (
            "default_high_cash_source_ingestion_key(\n        tenant_id=command.tenant_id",
            "*,\n    tenant_id: str,\n    portfolio_id: str",
            "{tenant_id}:{portfolio_id}:{as_of_date.isoformat()}",
        ),
    )
    _require_fragments(
        errors,
        SIGNAL_API_SUPPORT_MODULE,
        texts[SIGNAL_API_SUPPORT_MODULE],
        (
            'TENANT_SCOPE_PROVENANCE_ATTRIBUTE = "tenant_scope_provenance"',
            'TRUSTED_SINGLE_TENANT_PROVENANCE = "trusted_single_tenant"',
            "required_tenant_context_or_problem",
            "attributes=event_attributes",
        ),
    )
    _require_fragments(
        errors,
        API_BASE_MODEL_MODULE,
        texts[API_BASE_MODEL_MODULE],
        ('ConfigDict(populate_by_name=True, extra="forbid")',),
    )
    _require_fragments(
        errors,
        OBSERVABILITY_MODULE,
        texts[OBSERVABILITY_MODULE],
        ('"tenant_id"', '"tenant_ids"'),
    )
    for relative_path in CORE_API_MODULES:
        _require_fragments(
            errors,
            relative_path,
            texts[relative_path],
            ("require_tenant_context=True", "trusted caller context", "candidate access scope"),
        )

    test_fragments = {
        Path("tests/unit/test_high_cash_application.py"): (
            "test_core_backed_high_cash_candidate_identity_is_isolated_by_tenant",
        ),
        Path("tests/unit/test_source_ingestion.py"): (
            "test_generated_source_ingestion_identity_is_isolated_by_tenant",
        ),
        Path("tests/unit/test_lotus_core_sources.py"): (
            "test_lotus_core_adapter_propagates_each_explicit_tenant",
        ),
        Path("tests/integration/test_high_cash_signal_api.py"): (
            "test_high_cash_source_api_requires_one_trusted_tenant_before_runtime",
            "test_high_cash_source_api_rejects_ambiguous_tenant_context",
            "test_high_cash_source_api_rejects_untrusted_tenant_override_before_runtime",
            "test_high_cash_source_api_rejects_body_tenant_override_before_runtime",
        ),
    }
    for relative_path, fragments in test_fragments.items():
        _require_fragments(errors, relative_path, texts[relative_path], fragments)
    return sorted(errors)


def _read_required_files(root: Path, errors: list[str]) -> dict[Path, str]:
    texts: dict[Path, str] = {}
    for relative_path in REQUIRED_FILES:
        path = root / relative_path
        if not path.is_file():
            errors.append(f"{relative_path.as_posix()}: required tenant-contract file is missing")
            continue
        texts[relative_path] = path.read_text(encoding="utf-8")
    return texts


def _require_fragments(
    errors: list[str],
    relative_path: Path,
    text: str,
    fragments: tuple[str, ...],
) -> None:
    for fragment in fragments:
        if fragment not in text:
            errors.append(
                f"{relative_path.as_posix()}: required tenant contract `{fragment}` is missing"
            )


def main() -> int:
    errors = validate_trusted_tenant_context()
    if errors:
        print("Trusted tenant context gate failed:")
        print("\n".join(errors))
        return 1
    print("Trusted tenant context gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
