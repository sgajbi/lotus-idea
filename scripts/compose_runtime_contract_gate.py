from pathlib import Path

from ci_release_evidence_contract import validate_compose_runtime_contract


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT / "docker-compose.yml"


def main() -> int:
    errors = validate_compose_runtime_contract(COMPOSE_PATH.read_text(encoding="utf-8"))
    if errors:
        print("Compose runtime contract failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Compose runtime contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
