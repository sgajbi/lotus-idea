import re
import sys
from pathlib import Path

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


def main() -> int:
    violations: list[str] = []
    for root_name in SCAN_ROOTS:
        root = Path(root_name)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path in ALLOWLIST:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for name, pattern in FORBIDDEN_PATTERNS.items():
                if pattern.search(text):
                    violations.append(f"{path}: forbidden sensitive content marker {name}")
    if violations:
        print("\\n".join(sorted(violations)))
        return 1
    print("No-sensitive-content guard passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
