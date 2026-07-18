from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.support.http import managed_test_client_scope


@pytest.fixture(autouse=True)
def _close_e2e_test_clients() -> Iterator[None]:
    with managed_test_client_scope():
        yield
