"""
Email Routes - API endpoints for email generation and sending
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone
from loguru import logger

from app.database import get_db, JobApplication, JobPosting, Resume
from app.email.smtp_service import email_service
from app.rag.generator import llm_generator

router = APIRouter(prefix="/email", tags=["email"])


class SendEmailRequest(BaseModel):
    application_id: str
    recipient_email: str
    attach_resume: bool = True
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None


class RegenerateEmailRequest(BaseModel):
    application_id: str
    feedback: Optional[str] = None


@router.post("/send")
async def send_application_email(
    payload: SendEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send an application email (requires user approval - this IS the approval step).
    User must explicitly call this endpoint to send.
    """
    # Fetch application
    result = await db.execute(
        select(JobApplication).where(JobApplication.id == payload.application_id)
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if application.status == "sent":
        raise HTTPException(status_code=400, detail="Application email already sent")

    # Fetch related data
    job_result = await db.execute(select(JobPosting).where(JobPosting.id == application.job_id))
    job = job_result.scalar_one_or_none()

    resume_result = await db.execute(select(Resume).where(Resume.id == application.resume_id))
    resume = resume_result.scalar_one_or_none()

    subject = payload.custom_subject or application.generated_subject or f"Application for {job.title if job else 'Position'}"
    body = payload.custom_body or application.generated_email or ""

    if not body:
        raise HTTPException(status_code=400, detail="No email body available. Please generate email first.")

    # Send email
    try:
        resume_path = resume.file_path if (payload.attach_resume and resume) else None
        await email_service.send_application_email(
            to_email=payload.recipient_email,
            subject=subject,
            body=body,
            resume_path=resume_path,
            candidate_name=resume.name if resume else None
        )

        # Update application status
        await db.execute(
            update(JobApplication)
            .where(JobApplication.id == payload.application_id)
            .values(
                status="sent",
                email_sent_at=datetime.now(timezone.utc),
                email_recipient=payload.recipient_email
            )
        )
        await db.commit()

        logger.info(f"✅ Email sent to {payload.recipient_email}")
        return {
            "message": "Email sent successfully",
            "recipient": payload.recipient_email,
            "subject": subject,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Email sending failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.post("/regenerate")
async def regenerate_email(
    payload: RegenerateEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """Regenerate email with optional feedback/instructions"""
    result = await db.execute(
        select(JobApplication).where(JobApplication.id == payload.application_id)
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Fetch job and resume
    job_result = await db.execute(select(JobPosting).where(JobPosting.id == application.job_id))
    job = job_result.scalar_one_or_none()

    resume_result = await db.execute(select(Resume).where(Resume.id == application.resume_id))
    resume = resume_result.scalar_one_or_none()

    if not job or not resume:
        raise HTTPException(status_code=404, detail="Related job or resume not found")

    # Build context
    from app.rag.vector_store import vector_store
    from app.rag.retriever import retriever_service

    matches = retriever_service.find_best_resume_match(job.description, top_k=1)
    if not matches:
        raise HTTPException(status_code=400, detail="Could not retrieve resume context")

    resume_db_dict = {
        "name": resume.name or "",
        "skills": resume.skills or [],
        "experience": resume.experience or [],
        "education": resume.education or [],
    }
    rag_context = retriever_service.build_rag_context(job.description, matches[0], resume_db_dict)

    # Add feedback to context if provided
    jd_text = job.description
    if payload.feedback:
        jd_text = f"Additional requirements: {payload.feedback}\n\n{jd_text}"

    email_result = await llm_generator.generate_application_email(
        jd_text=jd_text,
        resume_context=rag_context,
        candidate_name=resume.name or "Applicant",
        match_score=application.similarity_score or 0
    )

    # Update application
    await db.execute(
        update(JobApplication)
        .where(JobApplication.id == payload.application_id)
        .values(
            generated_subject=email_result.get("subject", ""),
            generated_email=email_result.get("body", ""),
            status="draft"
        )
    )
    await db.commit()

    return {
        "application_id": payload.application_id,
        "subject": email_result.get("subject"),
        "body": email_result.get("body"),
        "message": "Email regenerated successfully"
    }


@router.get("/applications")
async def list_applications(db: AsyncSession = Depends(get_db)):
    """List all job applications with their status"""
    result = await db.execute(
        select(JobApplication, JobPosting, Resume)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .join(Resume, JobApplication.resume_id == Resume.id)
        .order_by(JobApplication.created_at.desc())
        .limit(100)
    )
    rows = result.all()

    return [
        {
            "id": app.id,
            "job_title": job.title,
            "company": job.company,
            "resume_name": resume.original_filename,
            "candidate_name": resume.name,
            "similarity_score": app.similarity_score,
            "status": app.status.value if app.status else "draft",
            "generated_subject": app.generated_subject,
            "email_recipient": app.email_recipient,
            "email_sent_at": app.email_sent_at.isoformat() if app.email_sent_at else None,
            "created_at": app.created_at.isoformat() if app.created_at else None,
        }
        for app, job, resume in rows
    ]


@router.get("/applications/{application_id}")
async def get_application(application_id: str, db: AsyncSession = Depends(get_db)):
    """Get full details of a specific application"""
    result = await db.execute(
        select(JobApplication).where(JobApplication.id == application_id)
    )
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    return {
        "id": app.id,
        "job_id": app.job_id,
        "resume_id": app.resume_id,
        "similarity_score": app.similarity_score,
        "match_details": app.match_details,
        "generated_subject": app.generated_subject,
        "generated_email": app.generated_email,
        "generated_cover_letter": app.generated_cover_letter,
        "status": app.status.value if app.status else "draft",
        "email_recipient": app.email_recipient,
        "email_sent_at": app.email_sent_at.isoformat() if app.email_sent_at else None,
        "notes": app.notes,
        "created_at": app.created_at.isoformat() if app.created_at else None
    }


@router.patch("/applications/{application_id}/status")
async def update_application_status(
    application_id: str,
    status: str,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update application status (interview, offer, rejected, etc.)"""
    valid_statuses = ["pending", "draft", "sent", "rejected", "interview", "offer", "withdrawn"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {valid_statuses}")

    update_values = {"status": status}
    if notes:
        update_values["notes"] = notes

    await db.execute(
        update(JobApplication)
        .where(JobApplication.id == application_id)
        .values(**update_values)
    )
    await db.commit()

    return {"message": "Status updated", "application_id": application_id, "status": status}
