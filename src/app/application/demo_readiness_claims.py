from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, cast


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEMO_READINESS_CLAIM_MATRIX_PATH = Path(
    "contracts/demo-readiness/lotus-idea-demo-readiness-claim-matrix.v1.json"
)
SUPPORTED_FEATURES_PATH = Path("supported-features/supported-features.json")

REQUIRED_FALSE_FLAGS = (
    "demo_ready",
    "client_publication_ready",
    "supported_feature_promoted",
    "data_mesh_certified",
    "production_certified",
    "ai_runtime_certified",
    "authn_authz_certified",
    "full_workbench_journey_certified",
    "downstream_runtime_certified",
)
REQUIRED_SOURCE_OF_TRUTH = frozenset(
    {
        "rfc_slice_16",
        "archetype_contract",
        "supported_features",
        "demo_claims",
        "client_demo_operating_process",
        "wiki_demo_readiness",
        "contract_loader",
        "contract_gate",
    }
)
REQUIRED_CLAIM_CATEGORIES = frozenset(
    {
        "implemented_foundation",
        "bounded_internal_walkthrough",
        "blocked_external_proof",
        "prohibited_claim",
    }
)
SUPPORTED_CLAIM_STATUSES = frozenset(
    {
        "bounded_internal_only",
        "blocked_pending_proof",
        "prohibited",
    }
)
REQUIRED_DO_NOT_CLAIM_BOUNDARIES = frozenset(
    {
        "source-authority",
        "client-publication",
        "identity-authn-authz",
        "ai-governance",
        "downstream-realization",
    }
)
PROHIBITED_POSITIVE_CLAIM_PHRASES = (
    "is client-demo-ready",
    "is demo-ready",
    "is production-ready",
    "is client-publication-ready",
    "is a supported external product",
    "has supported external business features",
    "certified client scenarios",
    "autonomous advice",
    "generally available",
)
FORBIDDEN_SENSITIVE_MARKERS = (
    "account_number",
    "client_name",
    "client_secret",
    "raw_payload",
    "raw prompt",
    "secret=",
)


@dataclass(frozen=True)
class DemoReadinessClaim:
    claim_key: str
    claim_category: str
    claim_status: str
    audiences: tuple[str, ...]
    external_distribution_allowed: bool
    allowed_language: str
    prohibited_language: str
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    issue_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "audiences", tuple(self.audiences))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "blockers", tuple(self.blockers))
        object.__setattr__(self, "issue_refs", tuple(self.issue_refs))


@dataclass(frozen=True)
class DoNotClaimBoundary:
    boundary_key: str
    owner_boundary: str
    required_before_claim: tuple[str, ...]
    issue_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_before_claim", tuple(self.required_before_claim))
        object.__setattr__(self, "issue_refs", tuple(self.issue_refs))


@dataclass(frozen=True)
class CommercialProofPack:
    pack_status: str
    client_safe_distribution_ready: bool
    rfp_safe_distribution_ready: bool
    approved_internal_uses: tuple[str, ...]
    required_before_external_use: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "approved_internal_uses", tuple(self.approved_internal_uses))
        object.__setattr__(
            self,
            "required_before_external_use",
            tuple(self.required_before_external_use),
        )
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))


@dataclass(frozen=True)
class DemoReadinessClaimMatrixContract:
    contract_id: str
    contract_version: str
    repository: str
    governing_rfcs: tuple[str, ...]
    rfc_slices: tuple[str, ...]
    issue_refs: tuple[str, ...]
    canonical_portfolio_ref: str
    claim_posture: str
    readiness_flags: Mapping[str, bool]
    source_of_truth: Mapping[str, str]
    claim_matrix: tuple[DemoReadinessClaim, ...]
    do_not_claim: tuple[DoNotClaimBoundary, ...]
    commercial_proof_pack: CommercialProofPack

    def __post_init__(self) -> None:
        object.__setattr__(self, "governing_rfcs", tuple(self.governing_rfcs))
        object.__setattr__(self, "rfc_slices", tuple(self.rfc_slices))
        object.__setattr__(self, "issue_refs", tuple(self.issue_refs))
        object.__setattr__(
            self,
            "readiness_flags",
            MappingProxyType(dict(self.readiness_flags)),
        )
        object.__setattr__(self, "source_of_truth", MappingProxyType(dict(self.source_of_truth)))
        object.__setattr__(self, "claim_matrix", tuple(self.claim_matrix))
        object.__setattr__(self, "do_not_claim", tuple(self.do_not_claim))


def load_demo_readiness_claim_matrix(
    *,
    repository_root: Path = REPOSITORY_ROOT,
    contract_path: Path = DEMO_READINESS_CLAIM_MATRIX_PATH,
) -> DemoReadinessClaimMatrixContract:
    payload = json.loads((repository_root / contract_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("demo readiness claim matrix contract must be a JSON object")
    return demo_readiness_claim_matrix_from_payload(payload)


def demo_readiness_claim_matrix_from_payload(
    payload: Mapping[str, Any],
) -> DemoReadinessClaimMatrixContract:
    source_of_truth = payload.get("source_of_truth", {})
    claim_matrix = payload.get("claim_matrix", ())
    do_not_claim = payload.get("do_not_claim", ())
    commercial_pack = payload.get("commercial_proof_pack", {})

    if not isinstance(source_of_truth, dict):
        raise ValueError("demo readiness source_of_truth must be an object")
    if not isinstance(claim_matrix, list):
        raise ValueError("demo readiness claim_matrix must be a list")
    if not all(isinstance(claim, dict) for claim in claim_matrix):
        raise ValueError("demo readiness claim_matrix entries must be objects")
    if not isinstance(do_not_claim, list):
        raise ValueError("demo readiness do_not_claim must be a list")
    if not all(isinstance(boundary, dict) for boundary in do_not_claim):
        raise ValueError("demo readiness do_not_claim entries must be objects")
    if not isinstance(commercial_pack, dict):
        raise ValueError("demo readiness commercial_proof_pack must be an object")

    return DemoReadinessClaimMatrixContract(
        contract_id=str(payload.get("contract_id", "")),
        contract_version=str(payload.get("contract_version", "")),
        repository=str(payload.get("repository", "")),
        governing_rfcs=_strings(payload.get("governing_rfcs", ())),
        rfc_slices=_strings(payload.get("rfc_slices", ())),
        issue_refs=_strings(payload.get("issue_refs", ())),
        canonical_portfolio_ref=str(payload.get("canonical_portfolio_ref", "")),
        claim_posture=str(payload.get("claim_posture", "")),
        readiness_flags={flag: bool(payload.get(flag, True)) for flag in REQUIRED_FALSE_FLAGS},
        source_of_truth={str(key): str(value) for key, value in source_of_truth.items()},
        claim_matrix=tuple(
            _claim_from_payload(cast(Mapping[str, Any], claim)) for claim in claim_matrix
        ),
        do_not_claim=tuple(
            _boundary_from_payload(cast(Mapping[str, Any], boundary)) for boundary in do_not_claim
        ),
        commercial_proof_pack=_commercial_pack_from_payload(
            cast(Mapping[str, Any], commercial_pack)
        ),
    )


def validate_demo_readiness_claim_matrix(
    *,
    repository_root: Path = REPOSITORY_ROOT,
    contract_path: Path = DEMO_READINESS_CLAIM_MATRIX_PATH,
    supported_features_path: Path = SUPPORTED_FEATURES_PATH,
) -> list[str]:
    contract = load_demo_readiness_claim_matrix(
        repository_root=repository_root,
        contract_path=contract_path,
    )
    supported_features_payload = json.loads(
        (repository_root / supported_features_path).read_text(encoding="utf-8")
    )
    if not isinstance(supported_features_payload, dict):
        return ["supported-features registry must be a JSON object"]
    return validate_demo_readiness_claim_matrix_payload(
        contract,
        supported_features_payload=supported_features_payload,
        repository_root=repository_root,
    )


def validate_demo_readiness_claim_matrix_payload(
    contract: DemoReadinessClaimMatrixContract,
    *,
    supported_features_payload: Mapping[str, Any],
    repository_root: Path = REPOSITORY_ROOT,
) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_header(contract))
    errors.extend(_validate_source_of_truth(contract, repository_root=repository_root))
    errors.extend(_validate_claims(contract, repository_root=repository_root))
    errors.extend(_validate_do_not_claim(contract))
    errors.extend(_validate_commercial_pack(contract, repository_root=repository_root))
    errors.extend(_validate_supported_features_posture(supported_features_payload))
    errors.extend(_validate_no_sensitive_content(contract))
    return errors


def _claim_from_payload(payload: Mapping[str, Any]) -> DemoReadinessClaim:
    return DemoReadinessClaim(
        claim_key=str(payload.get("claim_key", "")),
        claim_category=str(payload.get("claim_category", "")),
        claim_status=str(payload.get("claim_status", "")),
        audiences=_strings(payload.get("audiences", ())),
        external_distribution_allowed=bool(payload.get("external_distribution_allowed", True)),
        allowed_language=str(payload.get("allowed_language", "")),
        prohibited_language=str(payload.get("prohibited_language", "")),
        evidence_refs=_strings(payload.get("evidence_refs", ())),
        blockers=_strings(payload.get("blockers", ())),
        issue_refs=_strings(payload.get("issue_refs", ())),
    )


def _boundary_from_payload(payload: Mapping[str, Any]) -> DoNotClaimBoundary:
    return DoNotClaimBoundary(
        boundary_key=str(payload.get("boundary_key", "")),
        owner_boundary=str(payload.get("owner_boundary", "")),
        required_before_claim=_strings(payload.get("required_before_claim", ())),
        issue_refs=_strings(payload.get("issue_refs", ())),
    )


def _commercial_pack_from_payload(payload: Mapping[str, Any]) -> CommercialProofPack:
    return CommercialProofPack(
        pack_status=str(payload.get("pack_status", "")),
        client_safe_distribution_ready=bool(payload.get("client_safe_distribution_ready", True)),
        rfp_safe_distribution_ready=bool(payload.get("rfp_safe_distribution_ready", True)),
        approved_internal_uses=_strings(payload.get("approved_internal_uses", ())),
        required_before_external_use=_strings(payload.get("required_before_external_use", ())),
        evidence_refs=_strings(payload.get("evidence_refs", ())),
    )


def _validate_header(contract: DemoReadinessClaimMatrixContract) -> list[str]:
    errors: list[str] = []
    if contract.contract_id != "lotus-idea-demo-readiness-claim-matrix":
        errors.append("demo readiness claim matrix contract_id is invalid")
    if contract.contract_version != "1.0.0":
        errors.append("demo readiness claim matrix contract_version must be 1.0.0")
    if contract.repository != "lotus-idea":
        errors.append("demo readiness claim matrix repository must be lotus-idea")
    if "RFC-0002" not in contract.governing_rfcs:
        errors.append("demo readiness claim matrix must be governed by RFC-0002")
    if "slice-16" not in contract.rfc_slices:
        errors.append("demo readiness claim matrix must be tied to slice-16")
    if "sgajbi/lotus-idea#697" not in contract.issue_refs:
        errors.append("demo readiness claim matrix must reference sgajbi/lotus-idea#697")
    if contract.canonical_portfolio_ref != "PB_SG_GLOBAL_BAL_001":
        errors.append("demo readiness claim matrix canonical portfolio ref must be governed")
    if contract.claim_posture != "bounded_internal_foundation_not_client_demo_ready":
        errors.append("demo readiness claim posture must remain bounded and not client-demo-ready")
    for flag, value in sorted(contract.readiness_flags.items()):
        if value:
            errors.append(f"demo readiness claim matrix must keep {flag} false")
    return errors


def _validate_source_of_truth(
    contract: DemoReadinessClaimMatrixContract,
    *,
    repository_root: Path,
) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_SOURCE_OF_TRUTH - set(contract.source_of_truth))
    if missing:
        errors.append("demo readiness source_of_truth missing keys: " + ", ".join(missing))
    for key, relative_path in sorted(contract.source_of_truth.items()):
        errors.extend(_validate_repo_ref(f"source_of_truth.{key}", relative_path, repository_root))
    return errors


def _validate_claims(
    contract: DemoReadinessClaimMatrixContract,
    *,
    repository_root: Path,
) -> list[str]:
    errors: list[str] = []
    categories = {claim.claim_category for claim in contract.claim_matrix}
    missing_categories = sorted(REQUIRED_CLAIM_CATEGORIES - categories)
    if missing_categories:
        errors.append("demo readiness claim categories missing: " + ", ".join(missing_categories))
    claim_keys = [claim.claim_key for claim in contract.claim_matrix]
    duplicates = sorted({key for key in claim_keys if claim_keys.count(key) > 1})
    if duplicates:
        errors.append("duplicate demo readiness claim keys: " + ", ".join(duplicates))
    for claim in contract.claim_matrix:
        if not claim.claim_key:
            errors.append("demo readiness claim_key is required")
        if claim.claim_category not in REQUIRED_CLAIM_CATEGORIES:
            errors.append(f"{claim.claim_key}: unsupported claim_category")
        if claim.claim_status not in SUPPORTED_CLAIM_STATUSES:
            errors.append(f"{claim.claim_key}: unsupported claim_status")
        if claim.external_distribution_allowed:
            errors.append(f"{claim.claim_key}: external distribution must remain false")
        if not claim.audiences:
            errors.append(f"{claim.claim_key}: audiences are required")
        if not claim.allowed_language:
            errors.append(f"{claim.claim_key}: allowed_language is required")
        if not claim.prohibited_language:
            errors.append(f"{claim.claim_key}: prohibited_language is required")
        if not claim.evidence_refs:
            errors.append(f"{claim.claim_key}: evidence_refs are required")
        if not claim.blockers:
            errors.append(f"{claim.claim_key}: blockers are required before promotion")
        if not claim.issue_refs:
            errors.append(f"{claim.claim_key}: issue_refs are required")
        if claim.claim_status == "prohibited" and claim.claim_category != "prohibited_claim":
            errors.append(
                f"{claim.claim_key}: prohibited status must use prohibited_claim category"
            )
        if claim.claim_category == "blocked_external_proof" and claim.claim_status != (
            "blocked_pending_proof"
        ):
            errors.append(f"{claim.claim_key}: blocked external proof must stay blocked")
        for issue_ref in claim.issue_refs:
            errors.extend(_validate_issue_ref(f"{claim.claim_key}.issue_refs", issue_ref))
        for evidence_ref in claim.evidence_refs:
            errors.extend(
                _validate_repo_ref(
                    f"{claim.claim_key}.evidence_refs", evidence_ref, repository_root
                )
            )
        errors.extend(_validate_allowed_language(claim))
    return errors


def _validate_do_not_claim(contract: DemoReadinessClaimMatrixContract) -> list[str]:
    errors: list[str] = []
    boundaries = {boundary.boundary_key for boundary in contract.do_not_claim}
    missing = sorted(REQUIRED_DO_NOT_CLAIM_BOUNDARIES - boundaries)
    if missing:
        errors.append("demo readiness do_not_claim missing boundaries: " + ", ".join(missing))
    for boundary in contract.do_not_claim:
        if not boundary.owner_boundary:
            errors.append(f"{boundary.boundary_key}: owner_boundary is required")
        if not boundary.required_before_claim:
            errors.append(f"{boundary.boundary_key}: required_before_claim is required")
        if not boundary.issue_refs:
            errors.append(f"{boundary.boundary_key}: issue_refs are required")
        for issue_ref in boundary.issue_refs:
            errors.extend(_validate_issue_ref(f"{boundary.boundary_key}.issue_refs", issue_ref))
    return errors


def _validate_commercial_pack(
    contract: DemoReadinessClaimMatrixContract,
    *,
    repository_root: Path,
) -> list[str]:
    errors: list[str] = []
    pack = contract.commercial_proof_pack
    if pack.pack_status != "internal_enablement_only":
        errors.append("commercial proof pack must remain internal_enablement_only")
    if pack.client_safe_distribution_ready:
        errors.append("commercial proof pack must not claim client-safe distribution readiness")
    if pack.rfp_safe_distribution_ready:
        errors.append("commercial proof pack must not claim RFP-safe distribution readiness")
    if not pack.approved_internal_uses:
        errors.append("commercial proof pack approved_internal_uses are required")
    if not pack.required_before_external_use:
        errors.append("commercial proof pack required_before_external_use is required")
    if not pack.evidence_refs:
        errors.append("commercial proof pack evidence_refs are required")
    for evidence_ref in pack.evidence_refs:
        errors.extend(
            _validate_repo_ref("commercial_proof_pack.evidence_refs", evidence_ref, repository_root)
        )
    return errors


def _validate_supported_features_posture(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("repository") != "lotus-idea":
        errors.append("supported-features repository must be lotus-idea")
    if payload.get("current_posture") != "foundation_only":
        errors.append("supported-features current_posture must remain foundation_only")
    features = payload.get("features")
    if not isinstance(features, list):
        errors.append("supported-features features must be a list")
    elif features:
        errors.append("supported-features features[] must remain empty for this claim matrix")
    return errors


def _validate_allowed_language(claim: DemoReadinessClaim) -> list[str]:
    lowered = claim.allowed_language.lower()
    return [
        f"{claim.claim_key}: allowed_language contains unsupported positive claim phrase `{phrase}`"
        for phrase in PROHIBITED_POSITIVE_CLAIM_PHRASES
        if phrase in lowered
    ]


def _validate_no_sensitive_content(contract: DemoReadinessClaimMatrixContract) -> list[str]:
    text = json.dumps(
        {
            "source_of_truth": dict(contract.source_of_truth),
            "claim_matrix": [claim.__dict__ for claim in contract.claim_matrix],
            "do_not_claim": [boundary.__dict__ for boundary in contract.do_not_claim],
            "commercial_proof_pack": contract.commercial_proof_pack.__dict__,
        },
        sort_keys=True,
    ).lower()
    return [
        f"demo readiness claim matrix contains forbidden sensitive marker `{marker}`"
        for marker in FORBIDDEN_SENSITIVE_MARKERS
        if marker in text
    ]


def _validate_repo_ref(label: str, value: str, repository_root: Path) -> list[str]:
    if value.startswith(("GET ", "POST ", "make ")):
        return []
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return [f"demo readiness {label} ref `{value}` must stay repository-relative"]
    if not (repository_root / path).exists():
        return [f"demo readiness {label} ref `{value}` is missing"]
    return []


def _validate_issue_ref(label: str, value: str) -> list[str]:
    if value.startswith("sgajbi/") and "#" in value and value.rsplit("#", 1)[1].isdigit():
        return []
    return [f"demo readiness {label} ref `{value}` must be a sgajbi/<repo>#<number> ref"]


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)
