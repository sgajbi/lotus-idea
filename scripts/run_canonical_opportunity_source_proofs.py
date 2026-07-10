from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Mapping

from app.application.missing_benchmark_performance_readiness_proof import (
    missing_benchmark_performance_readiness_proof_is_valid,
)
from app.application.performance_underperformance_live_proof import (
    performance_underperformance_live_proof_is_valid,
)
from app.application.risk_concentration_live_proof import risk_concentration_live_proof_is_valid


ROOT = Path(__file__).resolve().parents[1]
AGGREGATE_SCHEMA_VERSION = "lotus-idea.canonical-opportunity-source-proofs.v1"


@dataclass(frozen=True)
class ProofCase:
    name: str
    script_name: str
    output_name: str
    validator: Callable[[Mapping[str, Any]], bool]


PROOF_CASES = (
    ProofCase(
        name="risk_concentration",
        script_name="generate_risk_concentration_live_proof.py",
        output_name="risk-concentration-live-proof.json",
        validator=risk_concentration_live_proof_is_valid,
    ),
    ProofCase(
        name="performance_underperformance",
        script_name="generate_performance_underperformance_live_proof.py",
        output_name="performance-underperformance-live-proof.json",
        validator=performance_underperformance_live_proof_is_valid,
    ),
    ProofCase(
        name="performance_benchmark_readiness",
        script_name="generate_missing_benchmark_performance_readiness_proof.py",
        output_name="missing-benchmark-performance-readiness-proof.json",
        validator=missing_benchmark_performance_readiness_proof_is_valid,
    ),
)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        generated_at = _parse_instant(args.generated_at_utc, "generated-at-utc")
        evaluated_at = _parse_instant(args.evaluated_at_utc, "evaluated-at-utc")
        output_directory = Path(args.output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        summaries = _run_proofs(
            cases=PROOF_CASES,
            args=args,
            generated_at=generated_at,
            evaluated_at=evaluated_at,
            output_directory=output_directory,
            correlation_id=args.correlation_id,
            trace_id=args.trace_id,
        )
        payload = _aggregate_payload(
            generated_at=generated_at,
            evaluated_at=evaluated_at,
            portfolio_id=args.portfolio_id,
            as_of_date=args.as_of_date,
            correlation_id=args.correlation_id,
            trace_id=args.trace_id,
            summaries=summaries,
        )
        aggregate_path = output_directory / "canonical-opportunity-source-proofs.json"
        aggregate_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"canonical opportunity source proof configuration error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["certificationReady"] else 3


def _run_proofs(
    *,
    cases: tuple[ProofCase, ...],
    args: argparse.Namespace,
    generated_at: datetime,
    evaluated_at: datetime,
    output_directory: Path,
    correlation_id: str,
    trace_id: str,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for case in cases:
        output_path = output_directory / case.output_name
        command = _proof_command(
            case=case,
            args=args,
            generated_at=generated_at,
            evaluated_at=evaluated_at,
            output_path=output_path,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        artifact_valid = False
        artifact_error: str | None = None
        artifact_observation: dict[str, Any] = {}
        if output_path.is_file():
            try:
                artifact = json.loads(output_path.read_text(encoding="utf-8"))
                artifact_valid = isinstance(artifact, dict) and case.validator(artifact)
                if isinstance(artifact, dict):
                    artifact_observation = _artifact_observation(artifact)
                if not artifact_valid:
                    artifact_error = "proof_artifact_contract_invalid"
            except (OSError, json.JSONDecodeError, TypeError):
                artifact_error = "proof_artifact_unreadable"
        else:
            artifact_error = "proof_artifact_missing"
        summaries.append(
            {
                "name": case.name,
                "script": f"scripts/{case.script_name}",
                "exitCode": completed.returncode,
                "artifactPath": output_path.relative_to(ROOT).as_posix()
                if output_path.is_relative_to(ROOT)
                else str(output_path),
                "artifactValid": artifact_valid,
                "artifactError": artifact_error,
                "processOutputSuppressed": bool(completed.stdout or completed.stderr),
                "artifactObservation": artifact_observation,
            }
        )
    return summaries


def _artifact_observation(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Keep aggregate evidence useful without copying child process output."""
    observation: dict[str, Any] = {}
    for key in (
        "runStatus",
        "evaluationOutcome",
        "sourceEvidenceCurrent",
        "benchmarkContextAvailable",
        "benchmarkReadinessDiagnostic",
    ):
        if key in artifact:
            observation[key] = artifact[key]
    for key in ("proofBlockers", "sourceDiagnosticCodes", "reasonCodes", "unsupportedReasons"):
        value = artifact.get(key)
        if isinstance(value, list | tuple):
            observation[key] = [str(item) for item in value]
    return observation


def _proof_command(
    *,
    case: ProofCase,
    args: argparse.Namespace,
    generated_at: datetime,
    evaluated_at: datetime,
    output_path: Path,
    correlation_id: str,
    trace_id: str,
) -> list[str]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / case.script_name),
        "--portfolio-id",
        args.portfolio_id,
        "--as-of-date",
        args.as_of_date,
        "--generated-at-utc",
        _format_instant(generated_at),
        "--evaluated-at-utc",
        _format_instant(evaluated_at),
        "--output",
        str(output_path),
        "--correlation-id",
        correlation_id,
        "--trace-id",
        trace_id,
    ]
    if case.name == "performance_benchmark_readiness":
        command.extend(["--performance-base-url", args.performance_base_url])
    elif case.name == "performance_underperformance":
        command.extend(["--performance-base-url", args.performance_base_url])
    else:
        command.extend(["--risk-base-url", args.risk_base_url])
    if case.name in {"performance_underperformance", "performance_benchmark_readiness"}:
        if args.period_name:
            command.extend(["--period-name", args.period_name])
        if args.reporting_currency:
            command.extend(["--reporting-currency", args.reporting_currency])
    if args.timeout_seconds:
        command.extend(["--timeout-seconds", args.timeout_seconds])
    return command


def _aggregate_payload(
    *,
    generated_at: datetime,
    evaluated_at: datetime,
    portfolio_id: str,
    as_of_date: str,
    correlation_id: str,
    trace_id: str,
    summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    ready = all(
        summary["exitCode"] == 0 and summary["artifactValid"] for summary in summaries
    )
    return {
        "schemaVersion": AGGREGATE_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofType": "canonical_opportunity_source_proofs",
        "generatedAtUtc": _format_instant(generated_at),
        "evaluatedAtUtc": _format_instant(evaluated_at),
        "portfolioId": portfolio_id,
        "asOfDate": as_of_date,
        "correlationId": correlation_id,
        "traceId": trace_id,
        "certificationReady": ready,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "proofs": summaries,
        "nonProofBoundaries": [
            "no_data_mesh_certification",
            "no_gateway_workbench_product_proof",
            "no_client_publication_approval",
            "no_supported_feature_promotion",
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run and validate the canonical Lotus Idea opportunity source proofs."
    )
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--risk-base-url", required=True)
    parser.add_argument("--performance-base-url", required=True)
    parser.add_argument("--period-name", default="1Y")
    parser.add_argument("--reporting-currency")
    parser.add_argument("--timeout-seconds", default="5.0")
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--evaluated-at-utc", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--trace-id", required=True)
    parser.add_argument("--output-directory", required=True)
    return parser


def _parse_instant(value: str, field_name: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _format_instant(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    sys.exit(main())
