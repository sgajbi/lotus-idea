from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from app.application.proof_provenance import bind_aggregate_proof_provenance


def required_base_url_from_args(
    args: object,
    *,
    primary_attr: str,
    fallback_attr: str,
    primary_option: str,
    fallback_option: str,
    primary_env: str,
    fallback_env: str,
) -> str:
    base_url = str(getattr(args, primary_attr) or getattr(args, fallback_attr) or "").strip()
    if not base_url:
        raise ValueError(
            f"{primary_option}, {fallback_option}, {primary_env}, or {fallback_env} is required"
        )
    return base_url


def core_control_plane_base_url_from_args(
    args: object,
    *,
    control_plane_env: str,
    base_env: str,
) -> str:
    return required_base_url_from_args(
        args,
        primary_attr="core_query_control_plane_base_url",
        fallback_attr="core_base_url",
        primary_option="--core-query-control-plane-base-url",
        fallback_option="--core-base-url",
        primary_env=control_plane_env,
        fallback_env=base_env,
    )


def core_query_base_url_from_args(
    args: object,
    *,
    query_env: str,
    base_env: str,
) -> str:
    return required_base_url_from_args(
        args,
        primary_attr="core_query_base_url",
        fallback_attr="core_base_url",
        primary_option="--core-query-base-url",
        fallback_option="--core-base-url",
        primary_env=query_env,
        fallback_env=base_env,
    )


def parse_generated_at_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("generated-at-utc must be timezone-aware")
    return parsed.astimezone(UTC)


def timeout_seconds_from_args(args: object) -> float:
    try:
        timeout = float(getattr(args, "timeout_seconds"))
    except ValueError as exc:
        raise ValueError("timeout seconds must be numeric") from exc
    if timeout <= 0:
        raise ValueError("timeout seconds must be positive")
    return timeout


def write_json_payload(payload: dict[str, Any], *, output: str | None) -> None:
    if output and payload.get("generatedAtUtc"):
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        unbound_rendered = json.dumps(payload, indent=2, sort_keys=True)
        output_path.write_text(f"{unbound_rendered}\n", encoding="utf-8")
        proof_ref = output_path.as_posix()
        payload = bind_aggregate_proof_provenance(
            payload,
            artifact_path=output_path,
            proof_ref=proof_ref,
            repository_root=Path.cwd(),
        )
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{rendered}\n", encoding="utf-8")
        return
    print(rendered)
