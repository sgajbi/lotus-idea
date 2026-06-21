import json
import logging

from app.observability import configure_logging, log_event


def test_configure_logging_sets_product_safe_message_format() -> None:
    configure_logging()
    assert logging.getLogger().level in {logging.INFO, logging.WARNING}


def test_log_event_emits_structured_json(caplog) -> None:  # type: ignore[no-untyped-def]
    with caplog.at_level(logging.INFO, logger="lotus-idea"):
        log_event("idea.test", service="lotus-idea", status="ok")

    payload = json.loads(caplog.records[-1].message)
    assert payload == {
        "event": "idea.test",
        "service": "lotus-idea",
        "status": "ok",
    }
