"""
Resume Routes - API endpoints for resume upload, management, and embedding
"""
import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from loguru import logger

from app.database import get_db, Resume
from app.parser.resume_parser import resume_parser
from app.rag.vector_store import vector_store
from app.config import settings

router = APIRouter(prefix="/resumes", tags=["resumes"])


class ResumeResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    name: Optional[str]
    email: Optional[str]
    skills: List[str]
    is_embedded: bool
    file_type: str
    file_size: int
    created_at: Optional[str]

    class Config:
        from_attributes = True


async def process_resume_embedding(resume_id: str, file_path: str, db_session):
    """Background task: parse resume and generate embeddings"""
    try:
        logger.info(f"🔄 Processing resume embeddings: {resume_id}")

        # Parse resume
        parsed = resume_parser.parse(file_path)
        chunks = resume_parser.chunk_resume(parsed)

        # Prepare metadata for vector store
        metadata = {
            "resume_id": resume_id,
            "filename": os.path.basename(file_path),
            "name": parsed.get("name", ""),
            "email": parsed.get("email", ""),
            "skills": ",".join(parsed.get("skills", [])[:20]),
        }

        # Store in vector DB
        vector_store.add_resume_chunks(resume_id, chunks, metadata)

        # Update database record
        async with db_session() as session:
            await session.execute(
                update(Resume)
                .where(Resume.id == resume_id)
                .values(
                    full_text=parsed.get("full_text", ""),
                    name=parsed.get("name", ""),
                    email=parsed.get("email", ""),
                    phone=parsed.get("phone", ""),
                    skills=parsed.get("skills", []),
                    experience=parsed.get("experience", []),
                    education=parsed.get("education", []),
                    projects=parsed.get("projects", []),
                    certifications=parsed.get("certifications", []),
                    summary=parsed.get("summary", ""),
                    is_embedded=True
                )
            )
            await session.commit()

        logger.info(f"✅ Resume {resume_id} embedded successfully")

    except Exception as e:
        logger.error(f"❌ Resume embedding failed for {resume_id}: {e}")


@router.post("/upload", response_model=dict)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a resume (PDF or DOCX).
    Parsing and embedding happen asynchronously in the background.
    """
    # Validate file type
    allowed_types = [".pdf", ".docx", ".doc"]
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_types)}"
        )

    # Validate file size
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
        )

    # Generate unique ID and save file
    resume_id = str(uuid.uuid4())
    safe_filename = f"{resume_id}{file_ext}"
    file_path = os.path.join(settings.resume_upload_dir, safe_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    # Create database record
    resume = Resume(
        id=resume_id,
        filename=safe_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_type=file_ext.lstrip("."),
        file_size=len(content),
        is_embedded=False
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    # Schedule background processing
    from app.database.connection import AsyncSessionLocal
    background_tasks.add_task(
        process_resume_embedding,
        resume_id,
        file_path,
        AsyncSessionLocal
    )

    logger.info(f"✅ Resume uploaded: {file.filename} → {resume_id}")

    return {
        "id": resume_id,
        "message": "Resume uploaded successfully. Parsing and embedding in progress.",
        "filename": file.filename,
        "status": "processing"
    }


@router.get("/", response_model=List[dict])
async def list_resumes(db: AsyncSession = Depends(get_db)):
    """List all uploaded resumes"""
    result = await db.execute(
        select(Resume).where(Resume.is_active == True).order_by(Resume.created_at.desc())
    )
    resumes = result.scalars().all()

    return [
        {
            "id": r.id,
            "filename": r.original_filename,
            "name": r.name or "Processing...",
            "email": r.email or "",
            "skills": r.skills or [],
            "is_embedded": r.is_embedded,
            "file_type": r.file_type,
            "file_size": r.file_size,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in resumes
    ]


@router.get("/{resume_id}", response_model=dict)
async def get_resume(resume_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed information for a specific resume"""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return {
        "id": resume.id,
        "filename": resume.original_filename,
        "name": resume.name,
        "email": resume.email,
        "phone": resume.phone,
        "skills": resume.skills or [],
        "experience": resume.experience or [],
        "education": resume.education or [],
        "projects": resume.projects or [],
        "certifications": resume.certifications or [],
        "summary": resume.summary,
        "is_embedded": resume.is_embedded,
        "file_type": resume.file_type,
        "file_size": resume.file_size,
        "created_at": resume.created_at.isoformat() if resume.created_at else None
    }


@router.delete("/{resume_id}")
async def delete_resume(resume_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a resume and its embeddings"""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Delete from vector store
    vector_store.delete_resume(resume_id)

    # Delete file
    try:
        if os.path.exists(resume.file_path):
            os.remove(resume.file_path)
    except Exception as e:
        logger.warning(f"Could not delete file: {e}")

    # Soft delete in DB
    await db.execute(
        update(Resume).where(Resume.id == resume_id).values(is_active=False)
    )
    await db.commit()

    return {"message": "Resume deleted successfully", "id": resume_id}


@router.post("/{resume_id}/reembed")
async def reembed_resume(
    resume_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Re-generate embeddings for an existing resume"""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Delete old embeddings
    vector_store.delete_resume(resume_id)

    # Reset embedding status
    await db.execute(
        update(Resume).where(Resume.id == resume_id).values(is_embedded=False)
    )
    await db.commit()

    # Reschedule embedding
    from app.database.connection import AsyncSessionLocal
    background_tasks.add_task(
        process_resume_embedding,
        resume_id,
        resume.file_path,
        AsyncSessionLocal
    )

    return {"message": "Re-embedding started", "id": resume_id}
