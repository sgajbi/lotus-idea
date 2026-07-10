from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
API_PROOF_SCHEMA_VERSION = "lotus-idea.canonical-signal-api-proof.v1"
IDEA_BASE_URL_ENV = "LOTUS_IDEA_BASE_URL"


@dataclass(frozen=True)
class ApiProofCase:
    name: str
    path: str
    family: str
    source_authority: str


API_PROOF_CASES = (
    ApiProofCase(
        name="high_cash",
        path="/api/v1/idea-signals/high-cash/evaluate-from-source",
        family="high_cash",
        source_authority="lotus-core",
    ),
    ApiProofCase(
        name="concentration_risk",
        path="/api/v1/idea-signals/concentration-risk/evaluate-from-source",
        family="concentration",
        source_authority="lotus-risk",
    ),
    ApiProofCase(
        name="underperformance",
        path="/api/v1/idea-signals/underperformance/evaluate-from-source",
        family="underperformance",
        source_authority="lotus-performance",
    ),
    ApiProofCase(
        name="missing_benchmark",
        path="/api/v1/idea-signals/missing-benchmark/evaluate-from-source",
        family="missing_benchmark",
        source_authority="lotus-core",
    ),
)


def main(argv: list[str] | None = None) -> int:
    args = _parser(argv)
    try:
        generated_at = _parse_instant(args.generated_at_utc, "generated-at-utc")
        evaluated_at = _parse_instant(args.evaluated_at_utc, "evaluated-at-utc")
        summaries = _run_cases(
            base_url=args.idea_base_url,
            portfolio_id=args.portfolio_id,
            as_of_date=args.as_of_date,
            evaluated_at=_format_instant(evaluated_at),
            correlation_id=args.correlation_id,
            trace_id=args.trace_id,
            timeout_seconds=float(args.timeout_seconds),
            period_name=args.period_name,
            reporting_currency=args.reporting_currency,
        )
        payload = _aggregate_payload(
            generated_at=generated_at,
            evaluated_at=evaluated_at,
            portfolio_id=args.portfolio_id,
            as_of_date=args.as_of_date,
            idea_base_url=args.idea_base_url,
            correlation_id=args.correlation_id,
            trace_id=args.trace_id,
            summaries=summaries,
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"canonical signal API proof configuration error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["certificationReady"] else 3


def _run_cases(
    *,
    base_url: str,
    portfolio_id: str,
    as_of_date: str,
    evaluated_at: str,
    correlation_id: str,
    trace_id: str,
    timeout_seconds: float,
    period_name: str = "1Y",
    reporting_currency: str | None = "USD",
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for case in API_PROOF_CASES:
        payload = {
            "portfolioId": portfolio_id,
            "asOfDate": as_of_date,
            "evaluatedAtUtc": evaluated_at,
        }
        if case.name == "underperformance":
            payload["periodName"] = period_name
            if reporting_currency is not None:
                payload["reportingCurrency"] = reporting_currency
        try:
            status_code, response = _post_json(
                url=f"{base_url.rstrip('/')}{case.path}",
                payload=payload,
                headers=_caller_headers(
                    portfolio_id=portfolio_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                ),
                timeout_seconds=timeout_seconds,
            )
            valid = _response_is_valid(response, case=case)
            summaries.append(
                {
                    "name": case.name,
                    "path": case.path,
                    "statusCode": status_code,
                    "responseValid": valid,
                    "responseObservation": _response_observation(response),
                    "errorCode": None if valid else "api_response_contract_invalid",
                }
            )
        except HTTPError as exc:
            summaries.append(
                {
                    "name": case.name,
                    "path": case.path,
                    "statusCode": exc.code,
                    "responseValid": False,
                    "responseObservation": {},
                    "errorCode": f"http_status_{exc.code}",
                }
            )
        except (URLError, OSError, ValueError, json.JSONDecodeError) as exc:
            summaries.append(
                {
                    "name": case.name,
                    "path": case.path,
                    "statusCode": None,
                    "responseValid": False,
                    "responseObservation": {},
                    "errorCode": _safe_error_code(exc),
                }
            )
    return summaries


def _post_json(
    *,
    url: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read()
        decoded = json.loads(raw.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise ValueError("API response must be a JSON object")
        return int(response.status), decoded


def _caller_headers(*, portfolio_id: str, correlation_id: str, trace_id: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "canonical-signal-api-proof",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
        "X-Caller-Portfolio-Ids": portfolio_id,
        "X-Correlation-Id": correlation_id,
        "X-Trace-Id": trace_id,
    }


def _response_is_valid(response: Mapping[str, Any], *, case: ApiProofCase) -> bool:
    outcome = response.get("outcome")
    return (
        response.get("family") == case.family
        and response.get("sourceAuthority") == case.source_authority
        and outcome in {"candidate_created", "not_eligible", "suppressed", "blocked"}
        and isinstance(response.get("reasonCodes"), list)
        and isinstance(response.get("unsupportedReasons"), list)
        and response.get("supportedFeaturePromoted") is False
    )


def _response_observation(response: Mapping[str, Any]) -> dict[str, Any]:
    observation: dict[str, Any] = {}
    for key in ("outcome", "family", "sourceAuthority", "supportedFeaturePromoted"):
        if key in response:
            observation[key] = response[key]
    for key in ("reasonCodes", "unsupportedReasons"):
        value = response.get(key)
        if isinstance(value, list | tuple):
            observation[key] = [str(item) for item in value]
    return observation


def _aggregate_payload(
    *,
    generated_at: datetime,
    evaluated_at: datetime,
    portfolio_id: str,
    as_of_date: str,
    idea_base_url: str,
    correlation_id: str,
    trace_id: str,
    summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schemaVersion": API_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofType": "canonical_signal_api",
        "generatedAtUtc": _format_instant(generated_at),
        "evaluatedAtUtc": _format_instant(evaluated_at),
        "portfolioScope": "governed_canonical",
        "asOfDate": as_of_date,
        "ideaBaseUrl": idea_base_url,
        "correlationId": correlation_id,
        "traceId": trace_id,
        "certificationReady": all(summary["responseValid"] for summary in summaries),
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "proofs": summaries,
        "nonProofBoundaries": [
            "no_data_mesh_certification",
            "no_gateway_workbench_product_proof",
            "no_supported_feature_promotion",
        ],
    }


def _parser(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Certify canonical Lotus Idea source-backed API routes."
    )
    parser.add_argument("--idea-base-url", default=os.getenv(IDEA_BASE_URL_ENV), required=False)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--evaluated-at-utc", required=True)
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--trace-id", required=True)
    parser.add_argument("--timeout-seconds", default="5.0")
    parser.add_argument("--period-name", default="1Y")
    parser.add_argument("--reporting-currency", default="USD")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if not str(args.idea_base_url or "").strip():
        parser.error(f"--idea-base-url or {IDEA_BASE_URL_ENV} is required")
    return args


def _parse_instant(value: str, field_name: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _format_instant(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _safe_error_code(error: Exception) -> str:
    return type(error).__name__.lower()


if __name__ == "__main__":
    sys.exit(main())
