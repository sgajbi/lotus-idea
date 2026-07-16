from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from app.application.advise_source_product_evidence import (  # noqa: E402
    PROFILES,
    advise_source_product_source_contract_is_valid,
    build_advise_source_product_source_contract,
)
from app.domain.proof_evidence import EvidenceClass  # noqa: E402

try:
    from scripts.proof_source_safety import validate_forbidden_content  # noqa: E402
except ModuleNotFoundError:
    from proof_source_safety import validate_forbidden_content  # type: ignore[import-not-found,no-redef] # noqa: E402


FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "evaluationId",
    "holdingId",
    "idempotencyKey",
    "mandateId",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "sourceRoute",
    "traceId",
    "transactionId",
}
FORBIDDEN_TEXT_FRAGMENTS = {
    "PB_SG_GLOBAL_BAL_001",
    "request-body",
    "response-body",
    "advise-policy-evaluation:",
}


def validate_advise_source_product_source_contract(capability: str) -> list[str]:
    profile = PROFILES[capability]
    errors: list[str] = []
    with TemporaryDirectory() as temporary_directory:
        advise_root = Path(temporary_directory)
        _write_valid_advise_sources(advise_root)
        payload = build_advise_source_product_source_contract(
            generated_at_utc=datetime(2026, 7, 16, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
            advise_root=advise_root,
            profile=profile,
        )
        if not advise_source_product_source_contract_is_valid(payload, profile=profile):
            errors.append(f"{capability}: valid source-contract fixture should validate")
        if payload.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
            errors.append(f"{capability}: evidenceClass must be source_contract")
        if payload.get("sourceContractBlockersSatisfied") != list(profile.blockers_satisfied):
            errors.append(f"{capability}: blocker effects must match the capability profile")
        if any(payload.get("authorityClaims", {}).values()):
            errors.append(f"{capability}: source-contract evidence must grant no authority")

        missing_source = build_advise_source_product_source_contract(
            generated_at_utc=datetime(2026, 7, 16, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
            advise_root=advise_root / "missing",
            profile=profile,
        )
        if missing_source.get("sourceContractValid") is not False:
            errors.append(f"{capability}: missing producer source must fail closed")
        if advise_source_product_source_contract_is_valid(missing_source, profile=profile):
            errors.append(f"{capability}: missing producer source must not validate")

        for field, value in (
            ("evidenceClass", EvidenceClass.RUNTIME_EXECUTION.value),
            ("sourceContractBlockersSatisfied", ()),
            ("unknownClaim", True),
        ):
            mutated = deepcopy(payload)
            mutated[field] = value
            if advise_source_product_source_contract_is_valid(mutated, profile=profile):
                errors.append(f"{capability}: mutated `{field}` must not validate")

        mutated = deepcopy(payload)
        mutated["sourceAuthority"][0]["sha256"] = "0" * 64
        if advise_source_product_source_contract_is_valid(mutated, profile=profile):
            errors.append(f"{capability}: source-authority digest drift must not validate")

        mutated = deepcopy(payload)
        mutated["authorityClaims"]["supportedFeaturePromoted"] = True
        if advise_source_product_source_contract_is_valid(mutated, profile=profile):
            errors.append(f"{capability}: promotion claim inflation must not validate")

        validate_forbidden_content(
            payload,
            errors,
            FORBIDDEN_KEYS,
            FORBIDDEN_TEXT_FRAGMENTS,
        )
    return errors


def _write_valid_advise_sources(root: Path) -> None:
    product_path = root / "contracts/domain-data-products/lotus-advise-products.v1.json"
    telemetry_path = (
        root / "contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
    )
    product_path.parent.mkdir(parents=True, exist_ok=True)
    telemetry_path.parent.mkdir(parents=True, exist_ok=True)
    product_path.write_text(
        json.dumps(
            {
                "products": [
                    {
                        "product_name": "AdvisoryPolicyEvaluationRecord",
                        "product_version": "v1",
                        "owner_repository": "lotus-advise",
                        "authoritative_domain": "advisory_workflow",
                        "lifecycle_status": "active",
                        "required_trust_metadata": [
                            "product_name",
                            "product_version",
                            "generated_at",
                            "content_hash",
                            "correlation_id",
                        ],
                        "approved_consumers": ["lotus-idea"],
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    telemetry_path.write_text(
        json.dumps(
            {
                "contract_id": "lotus-domain-product-trust-telemetry-snapshot",
                "product_id": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
                "producer_repository": "lotus-advise",
                "source_repository": "lotus-advise",
                "product_name": "AdvisoryPolicyEvaluationRecord",
                "product_version": "v1",
                "blocking": {
                    "blocked": True,
                    "blocked_reason": "TRUST_TELEMETRY_STALE",
                    "blocked_summary": "Certification remains blocked pending current telemetry.",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate typed Lotus Advise source-product evidence."
    )
    parser.add_argument("--capability", choices=tuple(PROFILES), required=True)
    args = parser.parse_args(argv)
    errors = validate_advise_source_product_source_contract(args.capability)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Advise {args.capability} source-product evidence gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
