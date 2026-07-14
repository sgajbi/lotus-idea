from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


def require_successful_junit_tests(
    *,
    test_report_path: Path,
    governed_tests: tuple[tuple[str, str], ...],
    missing_test_message: str,
    failed_test_message: str,
) -> None:
    try:
        root = ET.parse(test_report_path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValueError("PostgreSQL test report is unavailable or malformed") from exc
    cases = tuple(root.iter("testcase"))
    for class_name, test_name in governed_tests:
        matching = [
            case
            for case in cases
            if case.get("classname") == class_name and case.get("name") == test_name
        ]
        if len(matching) != 1:
            raise ValueError(missing_test_message)
        if any(
            matching[0].find(outcome) is not None for outcome in ("failure", "error", "skipped")
        ):
            raise ValueError(f"{failed_test_message}: {test_name}")
    if any(_count(root, field) for field in ("failures", "errors")):
        raise ValueError("PostgreSQL runtime proof report contains failed tests")


def _count(root: ET.Element, field: str) -> int:
    values = [
        element.get(field, "0")
        for element in root.iter()
        if element.tag in {"testsuite", "testsuites"}
    ]
    try:
        return max((int(value) for value in values), default=0)
    except ValueError as exc:
        raise ValueError(f"PostgreSQL test report has invalid {field} count") from exc
