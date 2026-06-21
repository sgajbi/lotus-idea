.PHONY: install lint ci-contract-gate monetary-float-guard no-sensitive-content-guard data-mesh-contract-gate migration-contract-gate migration-execution-gate migrate migrate-rollback supported-features-gate endpoint-certification-gate typecheck architecture-boundary-gate architecture-boundary-report quality-baseline openapi-gate test test-unit test-integration test-e2e test-coverage coverage-gate security-audit check ci docker-build clean

VENV_DIR ?= .venv

ifeq ($(OS),Windows_NT)
VENV_PYTHON := $(VENV_DIR)/Scripts/python.exe
else
VENV_PYTHON := $(VENV_DIR)/bin/python
endif

install:
	python -m venv $(VENV_DIR)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e ".[dev]"

lint:
	$(VENV_PYTHON) -m ruff check .
	$(VENV_PYTHON) -m ruff format --check .
	$(MAKE) ci-contract-gate
	$(MAKE) monetary-float-guard
	$(MAKE) no-sensitive-content-guard
	$(MAKE) data-mesh-contract-gate
	$(MAKE) migration-contract-gate
	$(MAKE) migration-execution-gate
	$(MAKE) supported-features-gate
	$(MAKE) endpoint-certification-gate

ci-contract-gate:
	$(VENV_PYTHON) scripts/ci_contract_gate.py

monetary-float-guard:
	$(VENV_PYTHON) scripts/check_monetary_float_usage.py

no-sensitive-content-guard:
	$(VENV_PYTHON) scripts/no_sensitive_content_guard.py

data-mesh-contract-gate:
	$(VENV_PYTHON) scripts/data_mesh_contract_gate.py

migration-contract-gate:
	$(VENV_PYTHON) scripts/migration_contract_gate.py

migration-execution-gate:
	$(VENV_PYTHON) scripts/run_migrations.py --direction apply --dry-run
	$(VENV_PYTHON) scripts/run_migrations.py --direction rollback --dry-run

migrate:
	$(VENV_PYTHON) scripts/run_migrations.py --direction apply

migrate-rollback:
	$(VENV_PYTHON) scripts/run_migrations.py --direction rollback

supported-features-gate:
	$(VENV_PYTHON) scripts/supported_features_gate.py

endpoint-certification-gate:
	$(VENV_PYTHON) scripts/endpoint_certification_gate.py

typecheck:
	$(VENV_PYTHON) -m mypy --config-file mypy.ini

architecture-boundary-gate:
	$(VENV_PYTHON) scripts/architecture_boundary_gate.py --mode blocking

architecture-boundary-report:
	$(VENV_PYTHON) scripts/architecture_boundary_gate.py --mode report-only

quality-baseline: architecture-boundary-report
	$(VENV_PYTHON) scripts/generate_quality_baseline.py

openapi-gate:
	$(VENV_PYTHON) scripts/openapi_quality_gate.py

test:
	$(MAKE) test-unit

test-unit:
	$(VENV_PYTHON) -m pytest tests/unit

test-integration:
	$(VENV_PYTHON) -m pytest tests/integration

test-e2e:
	$(VENV_PYTHON) -m pytest tests/e2e

test-coverage:
	COVERAGE_FILE=.coverage.unit $(VENV_PYTHON) -m pytest tests/unit --cov=src --cov-report=
	COVERAGE_FILE=.coverage.integration $(VENV_PYTHON) -m pytest tests/integration --cov=src --cov-report=
	COVERAGE_FILE=.coverage.e2e $(VENV_PYTHON) -m pytest tests/e2e --cov=src --cov-report=
	$(MAKE) coverage-gate

coverage-gate:
	$(VENV_PYTHON) scripts/coverage_gate.py

security-audit:
	$(VENV_PYTHON) -m pip_audit -r requirements/shared-runtime.lock.txt -r requirements/ci-tooling.lock.txt

check: lint typecheck architecture-boundary-gate openapi-gate migration-contract-gate migration-execution-gate supported-features-gate endpoint-certification-gate test

ci: lint typecheck architecture-boundary-gate openapi-gate migration-contract-gate migration-execution-gate supported-features-gate endpoint-certification-gate test-integration test-e2e test-coverage security-audit

docker-build:
	docker build -t backend-service:ci-test .

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache', '.ruff_cache', '.mypy_cache']]; [pathlib.Path(p).unlink(missing_ok=True) for p in ['.coverage', '.coverage.unit', '.coverage.integration', '.coverage.e2e']]"
