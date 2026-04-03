"""Tests for admin routes — analytics and feedback."""

import json
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.routes.admin import (
    log_job_analytics, _load_analytics, _save_analytics,
    _load_feedback, _save_feedback,
)
from backend.config import config


@pytest.fixture(autouse=True)
def clean_files(tmp_path, monkeypatch):
    """Use temp files for analytics/feedback."""
    analytics_f = str(tmp_path / "analytics.json")
    feedback_f = str(tmp_path / "feedback.json")
    monkeypatch.setattr(config, "ANALYTICS_FILE", analytics_f)
    monkeypatch.setattr(config, "FEEDBACK_FILE", feedback_f)
    yield


class TestAnalytics:
    def test_log_job_analytics(self):
        log_job_analytics(
            job_id="test-1",
            preset="cinematic_warm",
            mode="preset",
            duration=60.0,
            resolution="1920x1080",
            processing_time=12.5,
            success=True,
        )
        entries = _load_analytics()
        assert len(entries) == 1
        assert entries[0]["job_id"] == "test-1"
        assert entries[0]["preset"] == "cinematic_warm"
        assert entries[0]["success"] is True

    def test_multiple_entries(self):
        for i in range(5):
            log_job_analytics(
                job_id=f"job-{i}",
                preset="teal_orange",
                mode="preset",
                duration=30.0,
                resolution="1280x720",
                processing_time=8.0,
                success=i != 3,  # job-3 fails
            )
        entries = _load_analytics()
        assert len(entries) == 5
        assert sum(1 for e in entries if e["success"]) == 4
        assert sum(1 for e in entries if not e["success"]) == 1

    def test_empty_analytics(self):
        entries = _load_analytics()
        assert entries == []


class TestFeedback:
    def test_save_and_load_feedback(self):
        _save_feedback([
            {"job_id": "j1", "timestamp": time.time(), "rating": "great", "comment": ""},
        ])
        entries = _load_feedback()
        assert len(entries) == 1
        assert entries[0]["rating"] == "great"

    def test_multiple_feedback(self):
        entries = []
        for rating in ["great", "ok", "bad", "great", "great"]:
            entries.append({
                "job_id": f"j-{len(entries)}",
                "timestamp": time.time(),
                "rating": rating,
                "comment": "test" if rating == "bad" else "",
            })
        _save_feedback(entries)
        loaded = _load_feedback()
        assert len(loaded) == 5
        ratings = [e["rating"] for e in loaded]
        assert ratings.count("great") == 3
        assert ratings.count("bad") == 1

    def test_empty_feedback(self):
        entries = _load_feedback()
        assert entries == []


class TestAdminAPI:
    """Test admin API endpoints via FastAPI test client."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)

    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"

    def test_stats_without_key(self, client):
        resp = client.get("/api/admin/stats")
        assert resp.status_code == 403

    def test_stats_with_key(self, client):
        resp = client.get(
            "/api/admin/stats",
            headers={"x-api-key": config.ADMIN_API_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_jobs" in data
        assert "successful_jobs" in data

    def test_feedback_submit(self, client):
        resp = client.post("/api/admin/feedback", json={
            "job_id": "abcdef1234560000abcdef1234560000",
            "rating": "great",
            "comment": "",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_feedback_get_without_key(self, client):
        resp = client.get("/api/admin/feedback")
        assert resp.status_code == 403

    def test_feedback_get_with_key(self, client):
        # Submit one first
        client.post("/api/admin/feedback", json={
            "job_id": "abcdef1234560000abcdef1234560000",
            "rating": "ok",
            "comment": "decent",
        })
        resp = client.get(
            "/api/admin/feedback",
            headers={"x-api-key": config.ADMIN_API_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
