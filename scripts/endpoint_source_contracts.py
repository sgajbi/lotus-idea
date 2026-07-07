from __future__ import annotations

from typing import Any

SIGNAL_SOURCE_CONTRACT_ERROR_TERMS_BY_PATH = {
    "/api/v1/idea-signals/high-cash/evaluate": (
        "portfolioStateRef",
        "holdingsRef",
        "cashMovementRef",
        "cashflowProjectionRef",
    ),
    "/api/v1/idea-signals/allocation-drift/evaluate": (
        "actionRegisterRef",
        "mandatePerformanceHealthRef",
        "mandateRiskHealthRef",
    ),
    "/api/v1/idea-signals/low-income/evaluate": (
        "cashMovementRef",
        "cashflowProjectionRef",
    ),
    "/api/v1/idea-signals/underperformance/evaluate": ("performanceRef",),
    "/api/v1/idea-signals/bond-maturity/evaluate": (
        "holdingsRef",
        "maturityFactRef",
    ),
    "/api/v1/idea-signals/concentration-risk/evaluate": ("concentrationRef",),
    "/api/v1/idea-signals/drawdown-review/evaluate": ("drawdownRef",),
    "/api/v1/idea-signals/high-volatility/evaluate": ("riskRef",),
    "/api/v1/idea-signals/mandate-restriction/evaluate": ("restrictionRef",),
    "/api/v1/idea-signals/missing-risk-profile/evaluate": ("riskProfileRef",),
    "/api/v1/idea-signals/missing-benchmark/evaluate": ("benchmarkAssignmentRef",),
    "/api/v1/idea-signals/missing-suitability/evaluate": ("policyRef",),
}
SIGNAL_SOURCE_CONTRACT_FIELD_TERMS = tuple(
    sorted(
        {term for terms in SIGNAL_SOURCE_CONTRACT_ERROR_TERMS_BY_PATH.values() for term in terms}
    )
)


def validate_signal_source_contract_error_examples(endpoint: dict[str, Any]) -> list[str]:
    operation = (str(endpoint["method"]).upper(), str(endpoint["path"]))
    required_terms = SIGNAL_SOURCE_CONTRACT_ERROR_TERMS_BY_PATH.get(operation[1])
    if operation[0] != "POST" or required_terms is None:
        return []

    error_examples = [str(example) for example in endpoint.get("error_examples", [])]
    source_contract_examples = [
        example
        for example in error_examples
        if "sourceSystem" in example or "productId" in example or "source contract" in example
    ]
    if not source_contract_examples:
        return [
            f"{operation}: caller-supplied signal endpoint must document source-ref "
            "contract mismatch behavior"
        ]

    combined_examples = " ".join(source_contract_examples)
    errors: list[str] = []
    for term in required_terms:
        if term not in combined_examples:
            errors.append(f"{operation}: source-ref contract error example must mention `{term}`")

    allowed_terms = set(required_terms)
    forbidden_terms = [
        term
        for term in SIGNAL_SOURCE_CONTRACT_FIELD_TERMS
        if term not in allowed_terms and term in combined_examples
    ]
    if forbidden_terms:
        errors.append(
            f"{operation}: source-ref contract error example mentions unrelated fields: "
            f"{', '.join(forbidden_terms)}"
        )

    return errors
