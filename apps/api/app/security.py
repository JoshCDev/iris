"""Route guards for the demo/non-demo deployment boundary.

The production user-authentication layer does not exist in this research
prototype. Demo mode (the default) allows the interactive walkthrough on
loopback; non-demo mode refuses interactive routes instead of pretending
they are protected, and sensor ingest requires a configured device token.
"""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

from app.config import get_settings


def require_device_token(
    token: str | None = Header(default=None, alias="X-IRIS-Token"),
) -> None:
    """Sensor-ingest guard.

    - Demo mode with no configured token: allow (loopback-only demo).
    - Token configured: require a constant-time header match.
    - Non-demo with no token: refuse (defense in depth; ``validate_config``
      already refuses startup in this state).
    """
    expected = get_settings().iris_device_token
    if not expected:
        if get_settings().iris_demo_mode:
            return
        raise HTTPException(
            status_code=500,
            detail={"code": "non_demo_token_required",
                    "message": "IRIS_DEVICE_TOKEN must be configured when "
                               "IRIS_DEMO_MODE=0"})
    if token is None or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="bad token")


def require_demo_interaction() -> None:
    """Interactive plot/leaf/chat/confirmation routes are demo-mode only."""
    if get_settings().iris_demo_mode:
        return
    raise HTTPException(
        status_code=403,
        detail={"code": "non_demo_user_auth_required",
                "message": "Interactive endpoints require demo mode; "
                           "production user authentication is not part of "
                           "this research prototype."})
