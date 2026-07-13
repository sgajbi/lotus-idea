"""Outbox runtime composition."""

from app.runtime.outbox.publisher_state import build_outbox_publisher_from_environment

__all__ = ["build_outbox_publisher_from_environment"]
