from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_FEATURES_PATH = ROOT / "supported-features" / "supported-features.json"
SCAN_PATHS = (
    ROOT / "README.md",
    ROOT / "REPOSITORY-ENGINEERING-CONTEXT.md",
    ROOT / "docs" / "demo",
    ROOT / "docs" / "operations",
    ROOT / "quality",
    ROOT / "wiki",
)

PROMOTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "demo_ready": re.compile(r"\bdemo[- ]ready\b", re.IGNORECASE),
    "production_ready": re.compile(r"\bproduction[- ]ready\b", re.IGNORECASE),
    "externally_supported": re.compile(r"\bexternally supported\b", re.IGNORECASE),
    "supported_business_feature": re.compile(r"\bsupported business feature\b", re.IGNORECASE),
    "supported_product_capability": re.compile(
        r"\bsupported product (?:capability|claim|workflow)\b",
        re.IGNORECASE,
    ),
    "client_ready_publication": re.compile(r"\bclient[- ]ready publication\b", re.IGNORECASE),
    "certified_data_product": re.compile(r"\bcertified data product\b", re.IGNORECASE),
    "data_mesh_certified": re.compile(r"\bdata[- ]mesh certified\b", re.IGNORECASE),
    "live_source_ingestion": re.compile(r"\blive source ingestion\b", re.IGNORECASE),
    "gateway_workbench_support": re.compile(
        r"\bGateway/Workbench support\b",
        re.IGNORECASE,
    ),
    "platform_certified_true": re.compile(r"\bplatformCertified\s*=\s*true\b"),
    "supported_feature_promoted_true": re.compile(r"\bsupportedFeaturePromoted\s*=\s*true\b"),
}

QUALIFIED_CONTEXT_PATTERNS = (
    re.compile(r"\bnot\b", re.IGNORECASE),
    re.compile(r"\bno\b", re.IGNORECASE),
    re.compile(r"\bwithout\b", re.IGNORECASE),
    re.compile(r"\bunsupported\b", re.IGNORECASE),
    re.compile(r"\bplanned\b", re.IGNORECASE),
    re.compile(r"\bblocked\b", re.IGNORECASE),
    re.compile(r"\bpending\b", re.IGNORECASE),
    re.compile(r"\bbefore\b", re.IGNORECASE),
    re.compile(r"\buntil\b", re.IGNORECASE),
    re.compile(r"\brequires?\b", re.IGNORECASE),
    re.compile(r"\bdo(?:es)? not\b", re.IGNORECASE),
    re.compile(r"\bmust not\b", re.IGNORECASE),
    re.compile(r"\bcannot\b", re.IGNORECASE),
    re.compile(r"\bmust only\b", re.IGNORECASE),
    re.compile(r"\bonly after\b", re.IGNORECASE),
    re.compile(r"\bremain(?:s)?\b", re.IGNORECASE),
)


def _implemented_features_count(path: Path = SUPPORTED_FEATURES_PATH) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features", [])
    if not isinstance(features, list):
        return 0
    return sum(
        1
        for feature in features
        if isinstance(feature, dict) and feature.get("status") == "implemented"
    )


def _scan_files(paths: tuple[Path, ...] = SCAN_PATHS) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        files.extend(
            child
            for child in path.rglob("*")
            if child.is_file() and child.suffix.lower() in {".md", ".json"}
        )
    return files


def _is_qualified(lines: list[str], index: int) -> bool:
    window = " ".join(lines[max(0, index - 2) : index + 3])
    return any(pattern.search(window) for pattern in QUALIFIED_CONTEXT_PATTERNS)


def validate_implementation_truth(
    *,
    implemented_features_count: int | None = None,
    scan_paths: tuple[Path, ...] = SCAN_PATHS,
) -> list[str]:
    if implemented_features_count is None:
        implemented_features_count = _implemented_features_count()
    if implemented_features_count > 0:
        return []

    errors: list[str] = []
    for path in _scan_files(scan_paths):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(lines):
            for name, pattern in PROMOTION_PATTERNS.items():
                if pattern.search(line) and not _is_qualified(lines, index):
                    relative_path = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
                    errors.append(
                        f"{relative_path}:{index + 1}: unqualified current-state "
                        f"promotion claim `{name}` while no supported feature is implemented"
                    )
    return errors


def main() -> int:
    errors = validate_implementation_truth()
    if errors:
        print("\n".join(sorted(errors)))
        return 1
    print("Implementation-truth gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
