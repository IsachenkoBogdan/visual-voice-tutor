from __future__ import annotations

import os

from fastapi.testclient import TestClient

from visual_voice_tutor.config.settings import get_settings
from visual_voice_tutor.main import create_app


def test_product_profiles_and_sessions_flow() -> None:
    app = create_app()
    with TestClient(app) as client:
        learner_id = "learner_alpha"
        user_id = "user_alpha"

        link = client.put(f"/api/v1/accounts/{user_id}/learners/{learner_id}")
        assert link.status_code == 200

        profile_payload = {
            "learner_id": learner_id,
            "display_name": "Masha",
            "grade_band": "4-7",
            "pace_preference": "slow",
            "weak_spots": ["fractions"],
            "recurring_mistakes": ["distribution_errors"],
            "recent_topics": ["linear_equations"],
        }
        upsert_profile = client.put(f"/api/v1/learners/{learner_id}", json=profile_payload)
        assert upsert_profile.status_code == 200
        assert upsert_profile.json()["display_name"] == "Masha"

        with client.websocket_connect(f"/ws?session_id=sess_alpha&learner_id={learner_id}&user_id={user_id}") as ws:
            ws.send_json({"type": "run_mock_turn"})
            while True:
                message = ws.receive_json()
                if message["type"] == "final":
                    break

        learners_resp = client.get(f"/api/v1/accounts/{user_id}/learners")
        assert learners_resp.status_code == 200
        learners = learners_resp.json()
        assert any(item["learner_id"] == learner_id for item in learners)

        sessions_resp = client.get(f"/api/v1/learners/{learner_id}/sessions")
        assert sessions_resp.status_code == 200
        sessions = sessions_resp.json()
        assert len(sessions) >= 1
        assert sessions[0]["learner_id"] == learner_id

        usage_resp = client.get(f"/api/v1/billing/usage/{learner_id}")
        assert usage_resp.status_code == 200
        usage = usage_resp.json()
        assert any(item["event_type"] == "turn_completed" for item in usage)


def test_entitlement_blocks_when_limit_exceeded() -> None:
    app = create_app()
    with TestClient(app) as client:
        learner_id = "learner_blocked"

        set_sub = client.put(
            f"/api/v1/billing/subscription/{learner_id}",
            json={
                "learner_id": learner_id,
                "plan_id": "free",
                "status": "active",
                "renews_at": None,
                "monthly_turn_limit": 0,
            },
        )
        assert set_sub.status_code == 200

        with client.websocket_connect(f"/ws?session_id=sess_blocked&learner_id={learner_id}") as ws:
            ws.send_json({"type": "run_mock_turn"})
            first = ws.receive_json()
            second = ws.receive_json()

        assert first["type"] == "status"
        assert first["payload"]["stage"] == "entitlement_blocked"
        assert second["type"] == "error"
        assert second["payload"]["code"] == "entitlement_blocked"


def test_auth_gate_for_product_api() -> None:
    os.environ["API_AUTH_ENABLED"] = "true"
    os.environ["API_AUTH_TOKEN"] = "secret-token"
    try:
        get_settings.cache_clear()
        app = create_app()
        with TestClient(app) as client:
            unauthorized = client.get("/api/v1/billing/plans")
            assert unauthorized.status_code == 401

            authorized = client.get("/api/v1/billing/plans", headers={"x-api-key": "secret-token"})
            assert authorized.status_code == 200
    finally:
        os.environ.pop("API_AUTH_ENABLED", None)
        os.environ.pop("API_AUTH_TOKEN", None)
        get_settings.cache_clear()
