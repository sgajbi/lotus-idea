from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, TypeVar

CommandT = TypeVar("CommandT")
ResultT = TypeVar("ResultT")

ReceiptPair = tuple[dict[str, Any] | None, dict[str, Any] | None]
ReceiptBuilder = Callable[[CommandT, ResultT], ReceiptPair]
PayloadBuilder = Callable[
    [
        datetime,
        CommandT,
        str,
        bool,
        Mapping[str, Any] | None,
        Mapping[str, Any] | None,
        tuple[str, ...],
    ],
    dict[str, Any],
]
DiagnosticReader = Callable[[ResultT], Collection[str]]


@dataclass(frozen=True)
class RiskRuntimeExecutionBuilder(Generic[CommandT, ResultT]):
    build_receipts: ReceiptBuilder[CommandT, ResultT]
    build_payload: PayloadBuilder[CommandT]
    read_diagnostics: DiagnosticReader[ResultT]

    def build_completed(
        self,
        *,
        generated_at_utc: datetime,
        command: CommandT,
        result: ResultT,
        durable_storage_backed: bool,
    ) -> dict[str, Any]:
        require_timezone_aware(generated_at_utc, "generated_at_utc")
        source_receipt, persistence_receipt = self.build_receipts(command, result)
        blockers = runtime_qualification_blockers(
            durable_storage_backed=durable_storage_backed,
            source_receipt=source_receipt,
            persistence_receipt=persistence_receipt,
            diagnostic_codes=self.read_diagnostics(result),
        )
        return self.build_payload(
            generated_at_utc,
            command,
            "completed",
            durable_storage_backed,
            source_receipt,
            persistence_receipt,
            blockers,
        )

    def build_blocked(
        self,
        *,
        generated_at_utc: datetime,
        command: CommandT,
        error_code: str,
        durable_storage_backed: bool,
    ) -> dict[str, Any]:
        require_timezone_aware(generated_at_utc, "generated_at_utc")
        blockers = blocked_runtime_qualification_blockers(
            error_code=error_code,
            durable_storage_backed=durable_storage_backed,
        )
        return self.build_payload(
            generated_at_utc,
            command,
            "blocked",
            durable_storage_backed,
            None,
            None,
            blockers,
        )


def runtime_qualification_blockers(
    *,
    durable_storage_backed: bool,
    source_receipt: Mapping[str, Any] | None,
    persistence_receipt: Mapping[str, Any] | None,
    diagnostic_codes: Collection[str],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not durable_storage_backed:
        blockers.append("durable_repository_not_configured")
    if source_receipt is None:
        blockers.append("authoritative_source_receipt_missing")
    if persistence_receipt is None:
        blockers.append("persistence_receipt_missing")
    if any(
        code in {"risk_source_unavailable", "risk_source_entitlement_denied"}
        for code in diagnostic_codes
    ):
        blockers.append("risk_source_execution_blocked")
    return tuple(blockers)


def blocked_runtime_qualification_blockers(
    *,
    error_code: str,
    durable_storage_backed: bool,
) -> tuple[str, ...]:
    blockers = [f"source_error_{error_code.strip() or 'risk_source_unavailable'}"]
    if not durable_storage_backed:
        blockers.append("durable_repository_not_configured")
    blockers.extend(("authoritative_source_receipt_missing", "persistence_receipt_missing"))
    return tuple(blockers)


def require_timezone_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
