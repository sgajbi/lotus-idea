import json
import sys
from pathlib import Path

SUPPORTED_FEATURES_PATH = Path("supported-features/supported-features.json")


def main() -> int:
    if not SUPPORTED_FEATURES_PATH.exists():
        print(f"Missing {SUPPORTED_FEATURES_PATH}")
        return 1
    payload = json.loads(SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    if payload.get("repository") is None:
        errors.append("supported-features repository is required")
    if payload.get("policy") != "Only implementation-backed behavior may be promoted to supported.":
        errors.append("supported-features policy must preserve implementation-backed promotion")
    features = payload.get("features")
    if not isinstance(features, list):
        errors.append("supported-features features must be a list")
    else:
        for index, feature in enumerate(features):
            if not isinstance(feature, dict):
                errors.append(f"features[{index}] must be an object")
                continue
            status = feature.get("status")
            evidence = feature.get("promotion_evidence")
            if status == "implemented" and not evidence:
                errors.append(f"features[{index}] implemented feature missing promotion_evidence")
            if status not in {"planned", "implemented", "not_applicable"}:
                errors.append(f"features[{index}] invalid status {status!r}")
    if errors:
        print("\\n".join(errors))
        return 1
    print("Supported-features gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
