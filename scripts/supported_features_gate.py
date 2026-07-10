from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.application.supported_feature_promotion import (  # noqa: E402
    SUPPORTED_FEATURES_PATH,
    evaluate_supported_feature_promotion,
    validate_supported_features,
)

__all__ = ["validate_supported_features"]


def main() -> int:
    evaluation = evaluate_supported_feature_promotion(
        SUPPORTED_FEATURES_PATH,
        evaluated_at_utc=datetime.now(UTC),
    )
    if evaluation.validation_errors:
        print("\n".join(evaluation.validation_errors))
        return 1
    print("Supported-features gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
