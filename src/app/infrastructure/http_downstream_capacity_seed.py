from __future__ import annotations

from datetime import date, datetime
import hashlib
from typing import Any, Mapping

import httpx


MAX_RESPONSE_BYTES = 1_048_576
SYNTHETIC_TENANT_ID = "capacity-synthetic-tenant"
SYNTHETIC_BOOK_ID = "capacity-synthetic-book"
SYNTHETIC_PORTFOLIO_ID = "CAPACITY_SYNTHETIC_PORTFOLIO_001"
SYNTHETIC_CLIENT_ID = "capacity-synthetic-client"


class HttpDownstreamCapacitySeed:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        base_headers: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            headers=dict(base_headers or {}),
            transport=transport,
            follow_redirects=False,
        )

    def persist_candidate(self, *, seed_key: str, as_of_date: date, seeded_at_utc: datetime) -> str:
        response = self._post_json(
            "/api/v1/idea-signals/high-cash/evaluate-and-persist",
            payload=_candidate_payload(seed_key, as_of_date, seeded_at_utc),
            headers=_headers(
                subject="capacity-seed-automation",
                capability="idea.candidate.persist",
                idempotency_key=f"capacity-{seed_key}-persist",
            ),
        )
        persistence = response.get("persistence")
        candidate_id = persistence.get("candidateId") if isinstance(persistence, dict) else None
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            raise ValueError("capacity seed candidate response is missing candidateId")
        return candidate_id

    def transition_candidate(
        self,
        *,
        candidate_id: str,
        seed_key: str,
        target_status: str,
        changed_at_utc: datetime,
    ) -> None:
        self._post_json(
            f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
            payload={
                "transitionId": f"capacity-{seed_key}-{target_status}",
                "targetLifecycleStatus": target_status,
                "changedAtUtc": _utc_text(changed_at_utc),
                "reasonCodes": ["review_required"],
            },
            headers=_headers(
                subject="capacity-seed-automation",
                capability="idea.candidate.lifecycle.transition",
                idempotency_key=f"capacity-{seed_key}-{target_status}",
            ),
        )

    def approve_candidate(
        self, *, candidate_id: str, seed_key: str, decided_at_utc: datetime
    ) -> None:
        headers = _headers(
            subject="capacity-seed-advisor",
            capability="idea.review.record",
            idempotency_key=f"capacity-{seed_key}-review",
        )
        headers.update(
            {
                "X-Caller-Roles": "advisor",
                "X-Caller-Tenant-Ids": SYNTHETIC_TENANT_ID,
                "X-Caller-Book-Ids": SYNTHETIC_BOOK_ID,
                "X-Caller-Portfolio-Ids": SYNTHETIC_PORTFOLIO_ID,
                "X-Caller-Client-Ids": SYNTHETIC_CLIENT_ID,
            }
        )
        self._post_json(
            f"/api/v1/idea-candidates/{candidate_id}/review-actions",
            payload={
                "reviewId": f"capacity-{seed_key}-review",
                "action": "approve_for_conversion",
                "reasonCodes": ["review_required"],
                "decidedAtUtc": _utc_text(decided_at_utc),
            },
            headers=headers,
        )

    def record_conversion_intent(
        self,
        *,
        candidate_id: str,
        conversion_intent_id: str,
        seed_key: str,
        requested_at_utc: datetime,
    ) -> None:
        self._post_json(
            f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
            payload={
                "conversionIntentId": conversion_intent_id,
                "target": "advise_proposal",
                "reasonCodes": ["review_approved_for_conversion"],
                "requestedAtUtc": _utc_text(requested_at_utc),
            },
            headers=_headers(
                subject="capacity-seed-advisor",
                capability="idea.conversion.intent.record",
                idempotency_key=f"capacity-{seed_key}-conversion",
            ),
        )

    def close(self) -> None:
        self._client.close()

    def _post_json(
        self, path: str, *, payload: dict[str, Any], headers: Mapping[str, str]
    ) -> dict[str, Any]:
        try:
            response = self._client.post(path, json=payload, headers=dict(headers))
        except httpx.HTTPError as exc:
            raise ValueError("capacity seed API request failed") from exc
        if response.status_code != 200:
            raise ValueError(f"capacity seed API returned status {response.status_code}")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ValueError("capacity seed API response exceeded size limit")
        try:
            body = response.json()
        except ValueError as exc:
            raise ValueError("capacity seed API returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise ValueError("capacity seed API response must be an object")
        return body


def _candidate_payload(seed_key: str, as_of_date: date, seeded_at_utc: datetime) -> dict[str, Any]:
    return {
        "asOfDate": as_of_date.isoformat(),
        "evaluatedAtUtc": _utc_text(seeded_at_utc),
        "sourceReportedCashWeight": "0.18",
        "sourceEvidence": {
            "portfolioStateRef": _source_ref("PortfolioStateSnapshot", seed_key, as_of_date),
            "holdingsRef": _source_ref("HoldingsAsOf", seed_key, as_of_date),
            "cashMovementRef": _source_ref("PortfolioCashMovementSummary", seed_key, as_of_date),
            "cashflowProjectionRef": _source_ref(
                "PortfolioCashflowProjection", seed_key, as_of_date
            ),
        },
        "entitlementAllowed": True,
        "accessScope": _access_scope(),
    }


def _source_ref(product: str, seed_key: str, as_of_date: date) -> dict[str, str]:
    identity = f"lotus-core:{product}:v1:{seed_key}"
    return {
        "sourceSystem": "lotus-core",
        "productId": f"lotus-core:{product}:v1",
        "productVersion": "v1",
        "route": f"/capacity-seed/{product.lower()}",
        "asOfDate": as_of_date.isoformat(),
        "generatedAtUtc": f"{as_of_date.isoformat()}T00:00:00Z",
        "contentHash": f"sha256:{hashlib.sha256(identity.encode('utf-8')).hexdigest()}",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }


def _access_scope() -> dict[str, str]:
    return {
        "tenantId": SYNTHETIC_TENANT_ID,
        "bookId": SYNTHETIC_BOOK_ID,
        "portfolioId": SYNTHETIC_PORTFOLIO_ID,
        "clientId": SYNTHETIC_CLIENT_ID,
    }


def _headers(*, subject: str, capability: str, idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": subject,
        "X-Caller-Capabilities": capability,
        "X-Correlation-Id": f"capacity-{idempotency_key}",
        "Idempotency-Key": idempotency_key,
    }


def _utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
