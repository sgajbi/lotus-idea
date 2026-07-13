from __future__ import annotations

from pathlib import Path


ACTIONLINT_CONFIG_RELATIVE_PATH = Path(".github/actionlint.yaml")


def validate_actionlint_config(config: str) -> list[str]:
    required_fragments = (
        "self-hosted-runner:",
        "  labels:",
        "    - lotus-capacity-evidence",
        "    - lotus-deployment",
    )
    return [
        f".github/actionlint.yaml missing `{fragment.strip()}`"
        for fragment in required_fragments
        if fragment not in config
    ]


def validate_actionlint_governance(root: Path) -> list[str]:
    config_path = root / ACTIONLINT_CONFIG_RELATIVE_PATH
    if not config_path.exists():
        return ["Missing .github/actionlint.yaml"]
    return validate_actionlint_config(config_path.read_text(encoding="utf-8"))
