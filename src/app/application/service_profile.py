from __future__ import annotations

from app.domain.service_profile import DEFAULT_SERVICE_PROFILE, ServiceProfile


def current_service_profile() -> ServiceProfile:
    return DEFAULT_SERVICE_PROFILE
