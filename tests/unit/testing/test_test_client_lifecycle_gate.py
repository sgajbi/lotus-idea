from pathlib import Path

from scripts.testing.test_client_lifecycle_gate import find_unmanaged_test_client_violations


def test_gate_accepts_managed_integration_client(tmp_path: Path) -> None:
    test_file = tmp_path / "test_managed.py"
    test_file.write_text(
        "from tests.support.http import managed_test_client\n"
        "def test_api(app):\n"
        "    managed_test_client(app).get('/health')\n",
        encoding="utf-8",
    )

    assert find_unmanaged_test_client_violations(tmp_path) == []


def test_gate_rejects_direct_and_aliased_test_clients(tmp_path: Path) -> None:
    test_file = tmp_path / "test_unmanaged.py"
    test_file.write_text(
        "from fastapi.testclient import TestClient as Client\n"
        "import starlette.testclient as starlette_clients\n"
        "def test_api(app):\n"
        "    Client(app).get('/health')\n"
        "    starlette_clients.TestClient(app).get('/health')\n",
        encoding="utf-8",
    )

    violations = find_unmanaged_test_client_violations(tmp_path)

    assert len(violations) == 3
    assert any("import managed_test_client instead" in violation for violation in violations)
    assert sum("unmanaged TestClient construction" in violation for violation in violations) == 2
