# ruff: noqa: E402
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.demo_readiness_claims import (  # noqa: E402
    DEMO_READINESS_CLAIM_MATRIX_PATH,
    SUPPORTED_FEATURES_PATH,
    validate_demo_readiness_claim_matrix,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the Lotus Idea demo-readiness claim matrix posture."
    )
    parser.add_argument("--contract-path", type=Path, default=DEMO_READINESS_CLAIM_MATRIX_PATH)
    parser.add_argument("--supported-features-path", type=Path, default=SUPPORTED_FEATURES_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_demo_readiness_claim_matrix(
        contract_path=args.contract_path,
        supported_features_path=args.supported_features_path,
    )
    if errors:
        print("\n".join(errors))
        return 1
    print("Demo readiness claim matrix gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
