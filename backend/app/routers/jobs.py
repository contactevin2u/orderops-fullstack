from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Role
from ..auth.deps import require_roles
from ..services.background_jobs import job_service, process_job_worker
from ..utils.responses import envelope


router = APIRouter(
    prefix="/jobs",
    tags=["background-jobs"],
    dependencies=[Depends(require_roles(Role.ADMIN, Role.CASHIER))],
)


class CreateParseJobIn(BaseModel):
    text: str
    session_id: Optional[str] = None


class JobStatusOut(BaseModel):
    id: str
    job_type: str
    status: str
    progress: int
    progress_message: Optional[str]
    error_message: Optional[str]
    result_data: Optional[dict]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]


@router.post("/parse", response_model=dict)
def create_parse_job(
    body: CreateParseJobIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
):
    """
    Create a background parsing job for WhatsApp messages.
    Returns immediately with job ID for status tracking.
    """
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(400, "text is required")
    
    # Create job
    job = job_service.create_parse_job(
        db=db,
        text=text,
        session_id=body.session_id
    )
    
    # Worker will automatically pick up the job from the jobs table
    # No need to add to background_tasks anymore
    
    return envelope({
        "job_id": job.id,
        "status": "queued",
        "message": "Message queued for processing"
    })


@router.get("/{job_id}", response_model=dict)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_session),
):
    """Get the current status of a background job"""
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    result_data = None
    if job.result_data:
        import json
        try:
            result_data = json.loads(job.result_data)
        except:
            result_data = {"raw": job.result_data}
    
    return envelope({
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "progress": job.progress,
        "progress_message": job.progress_message,
        "error_message": job.error_message,
        "result_data": result_data,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    })


@router.get("", response_model=dict)
def list_jobs(
    session_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
):
    """List recent jobs for a session"""
    jobs = job_service.get_user_jobs(
        db=db,
        session_id=session_id,
        limit=limit
    )
    
    job_list = []
    for job in jobs:
        result_data = None
        if job.result_data:
            import json
            try:
                result_data = json.loads(job.result_data)
            except:
                result_data = {"raw": job.result_data}
        
        job_list.append({
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "progress": job.progress,
            "progress_message": job.progress_message,
            "error_message": job.error_message,
            "result_data": result_data,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        })
    
    return envelope({
        "jobs": job_list,
        "total": len(job_list)
    })


@router.delete("/cleanup", response_model=dict)
def cleanup_old_jobs(
    days_old: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_session),
):
    """Clean up old completed jobs"""
    job_service.cleanup_old_jobs(db, days_old)
    return envelope({"message": f"Cleaned up jobs older than {days_old} days"})