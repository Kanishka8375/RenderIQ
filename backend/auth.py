"""Per-job token authentication."""

import hmac

from fastapi import HTTPException, Request

from backend.services.job_manager import job_manager


def verify_job_token(job_id: str, request: Request) -> None:
    """Verify X-Job-Token header matches the stored access token for a job.

    Must be called AFTER validating job_id format and confirming the job exists.
    """
    token = request.headers.get("X-Job-Token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Missing X-Job-Token header")

    job = job_manager.get_job(job_id)
    if not job or not job.access_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not hmac.compare_digest(token, job.access_token):
        raise HTTPException(status_code=403, detail="Invalid job token")
