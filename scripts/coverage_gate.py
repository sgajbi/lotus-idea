import os
import sys
from argparse import ArgumentParser
from pathlib import Path

import coverage


DEFAULT_COVERAGE_FILES = (".coverage.unit", ".coverage.integration", ".coverage.e2e")


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(description="Combine Lotus coverage artifacts and enforce 99%.")
    parser.add_argument(
        "--coverage-dir",
        default=os.getenv("COVERAGE_DATA_DIR", "."),
        help="Directory containing .coverage.unit, .coverage.integration, and .coverage.e2e.",
    )
    args = parser.parse_args(argv)
    files = [Path(args.coverage_dir) / name for name in DEFAULT_COVERAGE_FILES]
    missing = [f for f in files if not Path(f).exists()]
    if missing:
        print(f"Missing coverage files: {missing}")
        return 1
    cov = coverage.Coverage()
    cov.combine(files)
    cov.save()
    total = cov.report()
    if total < 99.0:
        print(f"Coverage gate failed: {total:.2f} < 99.00")
        return 1
    print(f"Coverage gate passed: {total:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
