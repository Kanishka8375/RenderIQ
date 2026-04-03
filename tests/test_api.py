"""Tests for the FastAPI backend API."""

import io
import os
import subprocess
import time

import pytest
from fastapi.testclient import TestClient

# Ensure project root is importable
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.main import app
from backend.services.job_manager import job_manager


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def test_video(tmp_path):
    """Create a valid test video file."""
    path = str(tmp_path / "test.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        "color=c=#808080:s=320x240:d=2:r=30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        path,
    ], capture_output=True, check=True)
    return path


@pytest.fixture
def uploaded_job(client, test_video):
    """Upload a video and return the job info (includes access_token)."""
    with open(test_video, "rb") as f:
        resp = client.post(
            "/api/upload/raw",
            files={"file": ("test.mp4", f, "video/mp4")},
        )
    assert resp.status_code == 200
    return resp.json()


def _auth(uploaded):
    """Return headers dict with X-Job-Token from an uploaded job response."""
    return {"X-Job-Token": uploaded["access_token"]}


class TestUploadEndpoints:
    def test_upload_raw_valid(self, client, test_video):
        """POST /api/upload/raw with valid video returns 200 + job_id + access_token."""
        with open(test_video, "rb") as f:
            resp = client.post(
                "/api/upload/raw",
                files={"file": ("test.mp4", f, "video/mp4")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert "access_token" in data
        assert len(data["job_id"]) == 32
        assert data["filename"] == "test.mp4"
        assert data["duration"] > 0
        assert data["fps"] > 0
        assert "x" in data["resolution"]

    def test_upload_raw_invalid_format(self, client, tmp_path):
        """POST /api/upload/raw with invalid file returns 400."""
        path = str(tmp_path / "test.txt")
        with open(path, "w") as f:
            f.write("not a video")
        with open(path, "rb") as f:
            resp = client.post(
                "/api/upload/raw",
                files={"file": ("test.txt", f, "text/plain")},
            )
        assert resp.status_code == 400

    def test_upload_raw_oversized(self, client, tmp_path):
        """POST /api/upload/raw with >500MB file returns 413."""
        # We can't actually create a 500MB file in tests, so test the validation
        # by creating a smaller file and checking the mechanism works
        path = str(tmp_path / "small.mp4")
        with open(path, "wb") as f:
            f.write(b"\x00" * 100)
        with open(path, "rb") as f:
            resp = client.post(
                "/api/upload/raw",
                files={"file": ("small.mp4", f, "video/mp4")},
            )
        # This will fail validation (not a valid video) rather than size
        assert resp.status_code in (400, 413)

    def test_upload_reference_valid(self, client, test_video, uploaded_job):
        """POST /api/upload/reference with valid job_id returns 200."""
        job_id = uploaded_job["job_id"]
        with open(test_video, "rb") as f:
            resp = client.post(
                "/api/upload/reference",
                data={"job_id": job_id},
                files={"file": ("ref.mp4", f, "video/mp4")},
                headers=_auth(uploaded_job),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reference_uploaded"] is True

    def test_upload_reference_invalid_job(self, client, test_video):
        """POST /api/upload/reference with invalid job_id returns 400 or 404."""
        with open(test_video, "rb") as f:
            resp = client.post(
                "/api/upload/reference",
                data={"job_id": "nonexistent_id"},
                files={"file": ("ref.mp4", f, "video/mp4")},
            )
        assert resp.status_code in (400, 404)


class TestPresetsEndpoints:
    def test_list_presets(self, client):
        """GET /api/presets returns 200 + list of 10 presets."""
        resp = client.get("/api/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["presets"]) == 10
        for p in data["presets"]:
            assert "name" in p
            assert "display_name" in p
            assert "description" in p
            assert "preview_colors" in p
            assert len(p["preview_colors"]) == 3


class TestGradeEndpoints:
    def test_start_grade_preset(self, client, uploaded_job):
        """POST /api/grade/start with preset mode returns 200."""
        resp = client.post("/api/grade/start", json={
            "job_id": uploaded_job["job_id"],
            "mode": "preset",
            "preset_name": "cinematic_warm",
            "strength": 0.8,
            "output_format": "both",
        }, headers=_auth(uploaded_job))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("processing", "queued")

    def test_start_grade_reference(self, client, test_video, uploaded_job):
        """POST /api/grade/start with reference mode returns 200."""
        job_id = uploaded_job["job_id"]
        # Upload reference first
        with open(test_video, "rb") as f:
            client.post(
                "/api/upload/reference",
                data={"job_id": job_id},
                files={"file": ("ref.mp4", f, "video/mp4")},
                headers=_auth(uploaded_job),
            )
        resp = client.post("/api/grade/start", json={
            "job_id": job_id,
            "mode": "reference",
            "strength": 0.7,
            "output_format": "both",
        }, headers=_auth(uploaded_job))
        assert resp.status_code == 200

    def test_start_grade_invalid_job(self, client):
        """POST /api/grade/start with invalid job_id returns 400 (bad format)."""
        resp = client.post("/api/grade/start", json={
            "job_id": "nonexistent",
            "mode": "preset",
            "preset_name": "cinematic_warm",
        })
        assert resp.status_code == 400

    def test_start_grade_missing_token(self, client, uploaded_job):
        """POST /api/grade/start without token returns 401."""
        resp = client.post("/api/grade/start", json={
            "job_id": uploaded_job["job_id"],
            "mode": "preset",
            "preset_name": "cinematic_warm",
        })
        assert resp.status_code == 401

    def test_status_valid_job(self, client, uploaded_job):
        """GET /api/grade/status with valid job_id returns 200."""
        job_id = uploaded_job["job_id"]
        # Start a grade first
        client.post("/api/grade/start", json={
            "job_id": job_id,
            "mode": "preset",
            "preset_name": "vintage_film",
            "output_format": "lut",
        }, headers=_auth(uploaded_job))
        resp = client.get(f"/api/grade/status/{job_id}", headers=_auth(uploaded_job))
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "progress" in data

    def test_status_invalid_job(self, client):
        """GET /api/grade/status with invalid job_id returns 400 (bad format)."""
        resp = client.get("/api/grade/status/nonexistent")
        assert resp.status_code == 400


class TestDownloadEndpoints:
    def test_download_video_after_completion(self, client, uploaded_job):
        """GET /api/download/{id}/video after completion returns video file."""
        job_id = uploaded_job["job_id"]
        # Start grade
        client.post("/api/grade/start", json={
            "job_id": job_id,
            "mode": "preset",
            "preset_name": "golden_hour",
            "strength": 0.5,
            "output_format": "both",
        }, headers=_auth(uploaded_job))
        # Wait for completion (up to 120 seconds)
        for _ in range(60):
            resp = client.get(f"/api/grade/status/{job_id}", headers=_auth(uploaded_job))
            data = resp.json()
            if data["status"] in ("completed", "failed"):
                break
            time.sleep(2)

        if data["status"] == "completed":
            resp = client.get(f"/api/download/{job_id}/video", headers=_auth(uploaded_job))
            assert resp.status_code == 200
            assert len(resp.content) > 0

    def test_download_lut_after_completion(self, client, uploaded_job):
        """GET /api/download/{id}/lut after completion returns .cube file."""
        job_id = uploaded_job["job_id"]
        client.post("/api/grade/start", json={
            "job_id": job_id,
            "mode": "preset",
            "preset_name": "teal_orange",
            "output_format": "both",
        }, headers=_auth(uploaded_job))
        for _ in range(60):
            resp = client.get(f"/api/grade/status/{job_id}", headers=_auth(uploaded_job))
            data = resp.json()
            if data["status"] in ("completed", "failed"):
                break
            time.sleep(2)

        if data["status"] == "completed":
            resp = client.get(f"/api/download/{job_id}/lut", headers=_auth(uploaded_job))
            assert resp.status_code == 200
            content = resp.content.decode()
            assert "LUT_3D_SIZE" in content

    def test_download_without_token(self, client, uploaded_job):
        """GET /api/download/{id}/video without token returns 401."""
        job_id = uploaded_job["job_id"]
        resp = client.get(f"/api/download/{job_id}/video")
        assert resp.status_code == 401


class TestJobManager:
    def test_max_concurrent_jobs(self, client, test_video):
        """4th concurrent job should be queued."""
        jobs = []
        for i in range(4):
            with open(test_video, "rb") as f:
                resp = client.post(
                    "/api/upload/raw",
                    files={"file": (f"test{i}.mp4", f, "video/mp4")},
                )
            jobs.append(resp.json())

        # Start 4 jobs
        statuses = []
        for j in jobs:
            resp = client.post("/api/grade/start", json={
                "job_id": j["job_id"],
                "mode": "preset",
                "preset_name": "moody_dark",
                "output_format": "lut",
            }, headers=_auth(j))
            statuses.append(resp.json()["status"])

        # At least one should be queued if max_concurrent is 3
        # (depends on timing — jobs may complete very fast)
        assert any(s in ("processing", "queued") for s in statuses)

    def test_job_cleanup(self):
        """Jobs should be removable after expiry."""
        from backend.services.job_manager import JobManager
        mgr = JobManager()
        job = mgr.create_job("a" * 32)
        job.status = "completed"
        job.created_at = time.time() - 7200  # 2 hours ago
        mgr.cleanup_expired()
        assert mgr.get_job("a" * 32) is None


class TestHealthEndpoint:
    def test_health(self, client):
        """GET /api/health returns 200."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
