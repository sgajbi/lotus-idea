from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from pydantic import Field

from app.api.base_model import CamelModel

ROOT = Path(__file__).resolve().parents[2]


class ExampleCamelModel(CamelModel):
    review_queue_id: str = Field(..., alias="reviewQueueId")


def _load_api_camel_model_boundary_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "api_camel_model_boundary_gate.py"
    spec = importlib.util.spec_from_file_location("api_camel_model_boundary_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_camel_model_accepts_alias_and_field_name() -> None:
    assert ExampleCamelModel(reviewQueueId="queue-1").review_queue_id == "queue-1"
    assert (
        ExampleCamelModel.model_validate({"review_queue_id": "queue-2"}).review_queue_id
        == "queue-2"
    )
    assert ExampleCamelModel.model_validate({"review_queue_id": "queue-3"}).model_dump(
        by_alias=True
    ) == {
        "reviewQueueId": "queue-3",
    }


def test_api_camel_model_boundary_gate_passes_current_repository() -> None:
    module = _load_api_camel_model_boundary_gate()

    assert module.validate_api_camel_model_boundary() == []


def test_api_camel_model_boundary_gate_blocks_local_camel_model(tmp_path: Path) -> None:
    module = _load_api_camel_model_boundary_gate()
    api_dir = tmp_path / "src" / "app" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "unsafe_route.py").write_text(
        "from pydantic import BaseModel, ConfigDict\n\n"
        "class CamelModel(BaseModel):\n"
        "    model_config = ConfigDict(populate_by_name=True)\n",
        encoding="utf-8",
    )
    (api_dir / "base_model.py").write_text(
        "from pydantic import BaseModel, ConfigDict\n\n"
        "class CamelModel(BaseModel):\n"
        "    model_config = ConfigDict(populate_by_name=True)\n",
        encoding="utf-8",
    )

    errors = module.validate_api_camel_model_boundary(tmp_path)

    assert errors == [
        "src/app/api/unsafe_route.py:3: API DTO camel-case model configuration must be "
        "defined once in `app.api.base_model.CamelModel`",
        "src/app/api/unsafe_route.py:4: API DTO model alias configuration must use "
        "`app.api.base_model.CamelModel` instead of local ConfigDict",
    ]


def test_api_camel_model_boundary_gate_allows_shared_support_module(tmp_path: Path) -> None:
    module = _load_api_camel_model_boundary_gate()
    api_dir = tmp_path / "src" / "app" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "base_model.py").write_text(
        "from pydantic import BaseModel, ConfigDict\n\n"
        "class CamelModel(BaseModel):\n"
        "    model_config = ConfigDict(populate_by_name=True)\n",
        encoding="utf-8",
    )

    assert module.validate_api_camel_model_boundary(tmp_path) == []
