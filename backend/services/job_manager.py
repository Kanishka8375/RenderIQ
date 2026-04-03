"""Background job queue and status tracking with file-backed persistence.

Each job is stored as a JSON file under JOBS_DIR/{job_id}.json so that
job state survives container restarts and is visible to all workers.
"""

import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, fields

from backend.config import config
from backend.services.storage import cleanup_job

logger = logging.getLogger(__name__)

# Fields that hold transient runtime state and should not block persistence
_SERIALIZABLE_TYPES = (str, int, float, bool, type(None))


@dataclass
class JobInfo:
    job_id: str
    access_token: str = ""  # Per-job secret; required for all operations
    status: str = "pending"  # pending, queued, processing, completed, failed
    progress: int = 0
    current_step: str = ""
    start_time: float = 0
    end_time: float = 0
    error: str = ""
    raw_path: str = ""
    raw_filename: str = ""
    reference_path: str = ""
    graded_video_path: str = ""
    lut_path: str = ""
    preview_path: str = ""
    comparison_path: str = ""
    smart_grade_info: str = ""  # JSON-encoded smart grade analysis
    srt_path: str = ""
    thumbnail_path: str = ""
    duration: float = 0
    width: int = 0
    height: int = 0
    fps: float = 0
    file_size: int = 0
    created_at: float = field(default_factory=time.time)


def _job_path(job_id: str) -> str:
    """Return the filesystem path for a job's JSON state file."""
    return os.path.join(config.JOBS_DIR, f"{job_id}.json")


def _save_job(job: JobInfo) -> None:
    """Persist a job's state to disk."""
    path = _job_path(job.job_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(asdict(job), f)
        os.replace(tmp, path)
    except Exception:
        logger.exception("Failed to persist job %s", job.job_id)
        if os.path.exists(tmp):
            os.remove(tmp)


def _load_job(job_id: str) -> JobInfo | None:
    """Load a job's state from disk."""
    path = _job_path(job_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        # Only pass fields that exist on JobInfo
        valid_fields = {fld.name for fld in fields(JobInfo)}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return JobInfo(**filtered)
    except Exception:
        logger.exception("Failed to load job %s from disk", job_id)
        return None


class JobManager:
    def __init__(self):
        self._jobs: dict[str, JobInfo] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_JOBS)
        self._active_count = 0
        self._load_existing_jobs()

    def _load_existing_jobs(self):
        """Load any persisted jobs from disk on startup."""
        jobs_dir = config.JOBS_DIR
        if not os.path.isdir(jobs_dir):
            return
        for fname in os.listdir(jobs_dir):
            if not fname.endswith(".json"):
                continue
            job_id = fname[:-5]
            job = _load_job(job_id)
            if job:
                # Mark any previously-processing jobs as failed (unclean shutdown)
                if job.status in ("processing", "queued"):
                    job.status = "failed"
                    job.error = "Server restarted during processing"
                    job.end_time = time.time()
                    _save_job(job)
                self._jobs[job_id] = job
        logger.info("Loaded %d persisted jobs from disk", len(self._jobs))

    def create_job(self, job_id: str) -> JobInfo:
        with self._lock:
            job = JobInfo(job_id=job_id)
            self._jobs[job_id] = job
            _save_job(job)
            return job

    def get_job(self, job_id: str) -> JobInfo | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                return job
        # Fallback: try loading from disk (e.g. created by another worker)
        job = _load_job(job_id)
        if job:
            with self._lock:
                self._jobs[job_id] = job
        return job

    def update_job(self, job_id: str, **kwargs):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                for k, v in kwargs.items():
                    setattr(job, k, v)
                _save_job(job)

    def submit_grade_task(self, job_id: str, task_fn, *args, **kwargs):
        """Submit a grading task to the thread pool."""
        with self._lock:
            if self._active_count >= config.MAX_CONCURRENT_JOBS:
                job = self._jobs.get(job_id)
                if job:
                    job.status = "queued"
                    _save_job(job)
                    queue_pos = self._active_count - config.MAX_CONCURRENT_JOBS + 1
                    self._executor.submit(self._run_task, job_id, task_fn, *args, **kwargs)
                    return "queued", queue_pos
            self._active_count += 1

        self._executor.submit(self._run_task, job_id, task_fn, *args, **kwargs)
        return "processing", 0

    def _run_task(self, job_id: str, task_fn, *args, **kwargs):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "processing"
                job.start_time = time.time()
                _save_job(job)
                if self._active_count < config.MAX_CONCURRENT_JOBS:
                    self._active_count += 1
        try:
            task_fn(job_id, *args, **kwargs)
        except Exception as e:
            logger.exception("Job %s failed: %s", job_id, e)
            self.update_job(
                job_id, status="failed", error=str(e),
                end_time=time.time(),
            )
        finally:
            with self._lock:
                self._active_count = max(0, self._active_count - 1)

    def get_status(self, job_id: str) -> dict:
        """Get job status as a dict for API response."""
        with self._lock:
            job = self._jobs.get(job_id)

        # Fallback: try disk
        if not job:
            job = _load_job(job_id)
            if job:
                with self._lock:
                    self._jobs[job_id] = job

        if not job:
            return None

        elapsed = 0
        estimated = None
        if job.start_time > 0:
            elapsed = time.time() - job.start_time
            if job.progress > 0 and job.status == "processing":
                rate = elapsed / job.progress
                estimated = rate * (100 - job.progress)

        result = None
        if job.status == "completed":
            result = {
                "graded_video_url": f"/api/download/{job_id}/video" if job.graded_video_path else None,
                "lut_url": f"/api/download/{job_id}/lut" if job.lut_path else None,
                "preview_url": f"/api/download/{job_id}/preview" if job.preview_path else None,
                "comparison_url": f"/api/download/{job_id}/comparison" if job.comparison_path else None,
            }

        resp = {
            "job_id": job_id,
            "status": job.status,
            "progress": job.progress,
            "current_step": job.current_step,
            "elapsed_seconds": round(elapsed, 1),
            "estimated_remaining": round(estimated, 1) if estimated else None,
            "result": result,
        }
        if job.status == "queued":
            resp["queue_position"] = 1
        if job.status == "failed":
            resp["current_step"] = job.error

        # Include smart grade analysis if available
        if job.smart_grade_info:
            try:
                resp["smart_grade_info"] = json.loads(job.smart_grade_info)
            except (json.JSONDecodeError, TypeError):
                pass

        return resp

    def cleanup_expired(self):
        """Remove jobs older than expiry time."""
        now = time.time()
        expired = []
        with self._lock:
            for job_id, job in self._jobs.items():
                age = now - job.created_at
                if age > config.JOB_EXPIRY_SECONDS and job.status in ("completed", "failed"):
                    expired.append(job_id)

        for job_id in expired:
            cleanup_job(job_id)
            with self._lock:
                self._jobs.pop(job_id, None)
            # Remove persisted state file
            path = _job_path(job_id)
            if os.path.exists(path):
                os.remove(path)
            logger.info("Cleaned up expired job: %s", job_id)

    @property
    def active_count(self) -> int:
        with self._lock:
            return self._active_count


# Singleton
job_manager = JobManager()
