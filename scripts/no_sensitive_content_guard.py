import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATTERNS = {
    "portfolio_id": re.compile(r"\bportfolio[_-]?id\b", re.IGNORECASE),
    "client_id": re.compile(r"\bclient[_-]?id\b", re.IGNORECASE),
    "client_name": re.compile(r"\bclient[_-]?name\b", re.IGNORECASE),
    "account_id": re.compile(r"\baccount[_-]?id\b", re.IGNORECASE),
    "holding_id": re.compile(r"\bholding[_-]?id\b", re.IGNORECASE),
    "transaction_id": re.compile(r"\btransaction[_-]?id\b", re.IGNORECASE),
    "request_body": re.compile(r"\brequest[_-]?body\b", re.IGNORECASE),
    "response_body": re.compile(r"\bresponse[_-]?body\b", re.IGNORECASE),
    "raw_entitlement_failure": re.compile(r"\braw[_-]?entitlement[_-]?failure\b", re.IGNORECASE),
}

SCAN_ROOTS = ("evidence", "logs", "output")
ALLOWLIST = {
    Path("evidence/rfc-implementation/README.md"),
}


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _normalized_allowlist(allowlist: set[Path]) -> set[Path]:
    return {path.resolve() if path.is_absolute() else (ROOT / path).resolve() for path in allowlist}


def _scan_files(scan_roots: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for root in scan_roots:
        if not root.exists():
            continue
        if root.is_file():
            files.append(root)
            continue
        files.extend(path for path in root.rglob("*") if path.is_file())
    return files


def validate_no_sensitive_content(
    *,
    scan_roots: tuple[Path, ...] | None = None,
    allowlist: set[Path] | None = None,
) -> list[str]:
    roots = scan_roots or tuple(ROOT / root_name for root_name in SCAN_ROOTS)
    allowed_paths = _normalized_allowlist(allowlist or ALLOWLIST)
    violations: list[str] = []
    for path in _scan_files(roots):
        if path.resolve() in allowed_paths:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(text):
                violations.append(
                    f"{_display_path(path)}: forbidden sensitive content marker {name}"
                )
    return sorted(violations)


def main() -> int:
    violations = validate_no_sensitive_content()
    if violations:
        print("\\n".join(sorted(violations)))
        return 1
    print("No-sensitive-content guard passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
