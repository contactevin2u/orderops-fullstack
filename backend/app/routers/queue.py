from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_session
from ..models import Job, Role
from ..auth.deps import require_roles

router = APIRouter(
    prefix="/queue",
    tags=["queue"],
    dependencies=[Depends(require_roles(Role.ADMIN))],
)

class EnqueueParseCreate(BaseModel):
    text: str

@router.post("/parse-create", response_model=dict)
def enqueue_parse_create(body: EnqueueParseCreate, db: Session = Depends(get_session)):
    job = Job(kind="PARSE_CREATE", payload={"text": body.text}, status="queued")
    db.add(job); db.commit(); db.refresh(job)
    return {"job_id": job.id}


@router.post("/auto-assign", response_model=dict)  
def enqueue_auto_assign(db: Session = Depends(get_session)):
    """Queue auto-assignment job for background processing"""
    job = Job(kind="AUTO_ASSIGN", payload={}, status="queued")
    db.add(job); db.commit(); db.refresh(job)
    return {"job_id": job.id, "message": "Auto-assignment queued for background processing"}


@router.get("/jobs/{job_id}", response_model=dict)
def get_job(job_id: int, db: Session = Depends(get_session)):
    row = db.get(Job, job_id)
    if not row:
        return {"error": "not_found"}
    return {"id": row.id, "status": row.status, "attempts": row.attempts, "result": row.result, "last_error": row.last_error}
