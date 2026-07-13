from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]


def test_outbox_event_contract_gate_accepts_repo_contract() -> None:
    module = _load_contract_gate_script()

    assert module.validate_outbox_event_contract() == []


def test_outbox_event_contract_gate_rejects_supported_feature_overclaim(
    tmp_path: Path,
) -> None:
    module = _load_contract_gate_script()
    source_contract = ROOT / "contracts" / "outbox-events" / "lotus-idea-outbox-events.v1.json"
    contract = json.loads(source_contract.read_text(encoding="utf-8"))
    contract["supportedFeaturePromoted"] = True
    contract_path = tmp_path / "lotus-idea-outbox-events.v1.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    errors = module.validate_outbox_event_contract(contract_path=contract_path)

    assert "supportedFeaturePromoted must remain false before live certification" in errors


def test_outbox_event_contract_gate_rejects_runtime_contract_drift(tmp_path: Path) -> None:
    module = _load_contract_gate_script()
    source_contract = ROOT / "contracts" / "outbox-events" / "lotus-idea-outbox-events.v1.json"
    contract = json.loads(source_contract.read_text(encoding="utf-8"))
    contract["eventFamilies"][0]["eventType"] = "idea.uncontracted.event.v1"
    contract_path = tmp_path / "lotus-idea-outbox-events.v1.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    errors = module.validate_outbox_event_contract(contract_path=contract_path)

    assert "eventFamilies must list every implemented v1 event type in order" in errors


def test_outbox_event_contract_gate_rejects_conflated_example_lineage(tmp_path: Path) -> None:
    module = _load_contract_gate_script()
    source_contract = ROOT / "contracts" / "outbox-events" / "lotus-idea-outbox-events.v1.json"
    contract = json.loads(source_contract.read_text(encoding="utf-8"))
    contract["envelope"]["example"]["traceId"] = contract["envelope"]["example"]["causationId"]
    contract_path = tmp_path / "lotus-idea-outbox-events.v1.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    errors = module.validate_outbox_event_contract(contract_path=contract_path)

    assert "envelope.example must keep traceId distinct from causationId" in errors


def test_outbox_event_contract_gate_rejects_forbidden_contract_text(tmp_path: Path) -> None:
    module = _load_contract_gate_script()
    source_contract = ROOT / "contracts" / "outbox-events" / "lotus-idea-outbox-events.v1.json"
    contract = json.loads(source_contract.read_text(encoding="utf-8"))
    contract["payloadSafetyPolicy"]["failureReasonPolicy"] = "client-ready supported"
    contract_path = tmp_path / "lotus-idea-outbox-events.v1.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    errors = module.validate_outbox_event_contract(contract_path=contract_path)

    assert any(
        error.startswith("$.payloadSafetyPolicy.failureReasonPolicy: forbidden contract text")
        for error in errors
    )


def test_outbox_event_contract_gate_rejects_trace_causation_substitution(
    tmp_path: Path,
) -> None:
    module = _load_contract_gate_script()
    publisher_path = tmp_path / "src" / "app" / "infrastructure" / "outbox" / "publisher.py"
    publisher_path.parent.mkdir(parents=True)
    publisher_path.write_text("trace_id=event.causation_id\n", encoding="utf-8")
    original_root = getattr(module, "ROOT")
    setattr(module, "ROOT", tmp_path)
    try:
        errors: list[str] = []
        module._validate_lineage_implementation_alignment(errors)
    finally:
        setattr(module, "ROOT", original_root)

    assert "outbox publisher must propagate event.trace_id as transport trace" in errors
    assert "outbox publisher must not substitute causation_id for trace_id" in errors


def test_outbox_event_contract_gate_scans_every_persistence_writer(tmp_path: Path) -> None:
    module = _load_contract_gate_script()
    _write_persistence_event_writers(module, tmp_path, omit_last_event=True)
    original_root = getattr(module, "ROOT")
    setattr(module, "ROOT", tmp_path)
    try:
        errors: list[str] = []
        module._validate_persistence_event_writers(errors)
    finally:
        setattr(module, "ROOT", original_root)

    assert (
        f"implemented persistence event type missing: {module.REQUIRED_EVENT_TYPES[-1]}" in errors
    )


def test_outbox_event_contract_gate_rejects_missing_lineage_in_extracted_writer(
    tmp_path: Path,
) -> None:
    module = _load_contract_gate_script()
    _write_persistence_event_writers(module, tmp_path, omit_lineage_from_last_event=True)
    original_root = getattr(module, "ROOT")
    setattr(module, "ROOT", tmp_path)
    try:
        errors: list[str] = []
        module._validate_persistence_event_writers(errors)
    finally:
        setattr(module, "ROOT", original_root)

    assert any(
        module.REQUIRED_EVENT_TYPES[-1] in error and error.endswith("must pass event_lineage")
        for error in errors
    )


def _write_persistence_event_writers(
    module: ModuleType,
    root: Path,
    *,
    omit_last_event: bool = False,
    omit_lineage_from_last_event: bool = False,
) -> None:
    event_types = list(module.REQUIRED_EVENT_TYPES)
    split_at = len(event_types) - 2
    writer_event_types = (event_types[:split_at], event_types[split_at:])
    for relative_path, assigned_event_types in zip(
        module.PERSISTENCE_EVENT_WRITER_PATHS, writer_event_types, strict=True
    ):
        calls: list[str] = []
        for event_type in assigned_event_types:
            if omit_last_event and event_type == event_types[-1]:
                continue
            lineage = (
                "None"
                if omit_lineage_from_last_event and event_type == event_types[-1]
                else "event_lineage"
            )
            calls.append(
                f'self._append_outbox_event(event_type="{event_type}", event_lineage={lineage})'
            )
        source_path = root / relative_path
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(
            "def write(self, event_lineage):\n    " + "\n    ".join(calls) + "\n",
            encoding="utf-8",
        )


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "outbox" / "event_contract_gate.py"
    spec = importlib.util.spec_from_file_location("outbox_event_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
