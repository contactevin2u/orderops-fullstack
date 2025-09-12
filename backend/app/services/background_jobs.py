from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Text, Integer, func

from ..db import get_session
from ..models import Base
from .advanced_parser import advanced_parser


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    
    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type: str = Column(String(50), nullable=False)
    status: JobStatus = Column(String(20), nullable=False, default=JobStatus.PENDING)
    input_data: str = Column(Text, nullable=False)  # JSON string
    result_data: str = Column(Text, nullable=True)  # JSON string
    error_message: str = Column(Text, nullable=True)
    progress: int = Column(Integer, default=0)  # 0-100
    progress_message: str = Column(String(200), nullable=True)
    
    created_at: datetime = Column(DateTime, nullable=False, default=func.now())
    started_at: datetime = Column(DateTime, nullable=True)
    completed_at: datetime = Column(DateTime, nullable=True)
    
    # Metadata
    user_id: Optional[int] = Column(Integer, nullable=True)
    session_id: str = Column(String(100), nullable=True)


class BackgroundJobService:
    """Service for managing background jobs with real-time status updates"""
    
    def create_parse_job(self, db: Session, text: str, user_id: Optional[int] = None, session_id: Optional[str] = None) -> BackgroundJob:
        """Create a new parsing job"""
        job = BackgroundJob(
            job_type="parse_message",
            input_data=json.dumps({"text": text}),
            user_id=user_id,
            session_id=session_id,
            progress_message="Queued for processing..."
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    
    def get_job(self, db: Session, job_id: str) -> Optional[BackgroundJob]:
        """Get job by ID"""
        return db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
    
    def get_user_jobs(self, db: Session, user_id: Optional[int] = None, session_id: Optional[str] = None, limit: int = 50) -> List[BackgroundJob]:
        """Get recent jobs for a user or session"""
        query = db.query(BackgroundJob)
        
        if user_id:
            query = query.filter(BackgroundJob.user_id == user_id)
        elif session_id:
            query = query.filter(BackgroundJob.session_id == session_id)
            
        return (query.order_by(BackgroundJob.created_at.desc())
                .limit(limit)
                .all())
    
    def update_job_progress(self, db: Session, job_id: str, progress: int, message: str):
        """Update job progress"""
        try:
            # Direct update without fetching first to avoid session issues
            update_data = {
                'progress': progress,
                'progress_message': message
            }
            if progress == 0:
                update_data['status'] = JobStatus.PROCESSING
                update_data['started_at'] = datetime.utcnow()
            
            updated = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).update(update_data)
            if updated > 0:
                db.commit()
            else:
                print(f"⚠️ Job {job_id} not found for progress update")
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to update progress for job {job_id}: {e}")
    
    def complete_job(self, db: Session, job_id: str, result_data: Dict[str, Any]):
        """Mark job as completed with results"""
        try:
            # Direct update without fetching first to avoid session issues
            updated = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).update({
                'status': JobStatus.COMPLETED,
                'progress': 100,
                'progress_message': 'Processing completed successfully',
                'result_data': json.dumps(result_data),
                'completed_at': datetime.utcnow()
            })
            if updated > 0:
                db.commit()
                print(f"✅ Job {job_id} marked as completed")
            else:
                print(f"⚠️ Job {job_id} not found for completion")
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to complete job {job_id}: {e}")
    
    def fail_job(self, db: Session, job_id: str, error_message: str):
        """Mark job as failed"""
        try:
            # Direct update without fetching first to avoid session issues
            updated = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).update({
                'status': JobStatus.FAILED,
                'progress': -1,
                'progress_message': 'Processing failed',
                'error_message': error_message,
                'completed_at': datetime.utcnow()
            })
            if updated > 0:
                db.commit()
                print(f"✅ Job {job_id} marked as failed")
            else:
                print(f"⚠️ Job {job_id} not found for failure marking")
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to mark job {job_id} as failed: {e}")
    
    def process_parse_job(self, db: Session, job_id: str):
        """Process a parsing job in background"""
        job = self.get_job(db, job_id)
        if not job or job.status != JobStatus.PENDING:
            return
            
        try:
            # Update progress: Starting
            self.update_job_progress(db, job_id, 10, "Starting message analysis...")
            
            # Parse input
            input_data = json.loads(job.input_data)
            text = input_data["text"]
            
            # Update progress: Classifying
            self.update_job_progress(db, job_id, 25, "Classifying message type...")
            
            # Run advanced parsing
            result = advanced_parser.parse_whatsapp_message(db, text)
            
            # Update progress based on result type
            if result["status"] == "success":
                if result["type"] == "delivery":
                    self.update_job_progress(db, job_id, 75, f"Created new order: {result.get('order_code', 'N/A')}")
                elif result["type"] == "return":
                    self.update_job_progress(db, job_id, 75, f"Applied {result.get('adjustment_type', 'adjustment')} to order {result.get('mother_order_code', 'N/A')}")
            elif result["status"] == "order_not_found":
                self.update_job_progress(db, job_id, 60, "Could not find original order for adjustment")
            elif result["status"] == "unclear":
                self.update_job_progress(db, job_id, 30, "Message unclear - manual review needed")
            
            # Complete the job
            self.complete_job(db, job_id, result)
            
        except Exception as e:
            # The original session might be corrupted, so use a fresh one for error recording
            print(f"Job {job_id} processing failed: {str(e)}")
            try:
                # Close the corrupted session
                db.close()
            except Exception:
                pass
                
            # Use completely fresh session for error recording
            try:
                from ..db import get_session
                with next(get_session()) as fresh_db:
                    self.fail_job(fresh_db, job_id, f"Processing failed: {str(e)}")
            except Exception as final_error:
                print(f"Failed to record job failure for {job_id}: {final_error}")
                print(f"Original error was: {str(e)}")
    
    def cleanup_old_jobs(self, db: Session, days_old: int = 7):
        """Clean up jobs older than specified days"""
        cutoff = datetime.utcnow() - timedelta(days=days_old)
        db.query(BackgroundJob).filter(BackgroundJob.created_at < cutoff).delete()
        db.commit()


# Global service instance
job_service = BackgroundJobService()


def process_job_worker(job_id: str):
    """Worker function for Render background jobs"""
    db_session = None
    try:
        db_session = next(get_session())
        job_service.process_parse_job(db_session, job_id)
    except Exception as e:
        print(f"Worker failed to process job {job_id}: {str(e)}")
        # The process_parse_job method now handles its own error recording
        # with fresh sessions, so we don't need to do it here
    finally:
        # Always ensure session is closed
        if db_session:
            try:
                db_session.close()
            except Exception:
                pass