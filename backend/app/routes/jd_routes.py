"""
JD Routes - API endpoints for job description input and matching
"""
import os
import uuid
import tempfile
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from loguru import logger

from app.database import get_db, JobPosting, Resume, JobApplication, JobSource
from app.parser.jd_parser import jd_parser
from app.rag.retriever import retriever_service
from app.rag.generator import llm_generator
from app.rag.vector_store import vector_store
from app.config import settings

router = APIRouter(prefix="/jd", tags=["job-descriptions"])


class TextJDInput(BaseModel):
    text: str
    company: Optional[str] = None
    title: Optional[str] = None


class URLJDInput(BaseModel):
    url: str
    company: Optional[str] = None


class MatchRequest(BaseModel):
    job_id: str
    generate_email: bool = True
    generate_cover_letter: bool = False


@router.post("/text", response_model=dict)
async def submit_jd_text(
    payload: TextJDInput,
    db: AsyncSession = Depends(get_db)
):
    """Submit a job description as plain text"""
    jd_text = jd_parser.parse_text(payload.text)
    return await _process_jd(jd_text, db, company=payload.company, title=payload.title, source=JobSource.MANUAL)


@router.post("/pdf", response_model=dict)
async def submit_jd_pdf(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a PDF job description"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save to a cross-platform temp file
    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        temp_path = tmp.name

    try:
        jd_text = jd_parser.parse_pdf(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return await _process_jd(jd_text, db, source=JobSource.MANUAL)


@router.post("/image", response_model=dict)
async def submit_jd_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a screenshot/image of a job description (OCR)"""
    allowed_types = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Supported image formats: {', '.join(allowed_types)}"
        )

    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        temp_path = tmp.name

    try:
        jd_text = jd_parser.parse_image(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return await _process_jd(jd_text, db, source=JobSource.MANUAL)


@router.post("/url", response_model=dict)
async def submit_jd_url(
    payload: URLJDInput,
    db: AsyncSession = Depends(get_db)
):
    """Fetch and parse a job description from a URL"""
    jd_text = await jd_parser.parse_url(str(payload.url))
    return await _process_jd(
        jd_text, db,
        source_url=str(payload.url),
        company=payload.company,
        source=JobSource.URL
    )


@router.post("/match", response_model=dict)
async def match_jd_to_resumes(
    payload: MatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Core RAG endpoint: Find best matching resume for a job.
    Optionally generate email and cover letter.
    """
    # Fetch job from DB
    result = await db.execute(select(JobPosting).where(JobPosting.id == payload.job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    if not job.description:
        raise HTTPException(status_code=400, detail="Job has no description text")

    # Check we have resumes
    stats = vector_store.get_collection_stats()
    if stats["resume_chunks"] == 0:
        raise HTTPException(
            status_code=400,
            detail="No resumes are embedded yet. Please upload resumes first."
        )

    # RAG Step: Find best matching resumes
    logger.info(f"[MATCH] Matching job {payload.job_id} against resumes...")
    matches = retriever_service.find_best_resume_match(
        job.description,
        top_k=settings.top_k_results
    )

    if not matches:
        return {
            "job_id": payload.job_id,
            "matches": [],
            "message": "No suitable resume found. Please upload relevant resumes."
        }

    best_match = matches[0]
    best_resume_id = best_match["resume_id"]

    # Fetch resume from DB for structured data
    res_result = await db.execute(select(Resume).where(Resume.id == best_resume_id))
    resume_db = res_result.scalar_one_or_none()

    # Build detailed match info
    resume_skills = resume_db.skills if resume_db else []
    job_skills = job.skills_required or []

    detailed_match = retriever_service.compute_detailed_match(
        job_skills, resume_skills, best_match["score"]
    )

    # Build RAG context
    resume_db_dict = {}
    if resume_db:
        resume_db_dict = {
            "name": resume_db.name or "",
            "email": resume_db.email or "",
            "skills": resume_db.skills or [],
            "experience": resume_db.experience or [],
            "education": resume_db.education or [],
        }

    rag_context = retriever_service.build_rag_context(
        job.description, best_match, resume_db_dict
    )

    candidate_name = resume_db.name if resume_db else "Applicant"

    response_data = {
        "job_id": payload.job_id,
        "job_title": job.title,
        "company": job.company,
        "best_match": {
            "resume_id": best_resume_id,
            "resume_name": resume_db.original_filename if resume_db else "Unknown",
            "candidate_name": candidate_name,
            "semantic_score": best_match["score"],
            "overall_score": detailed_match["overall_score"],
            "skill_match_percentage": detailed_match["skill_match_percentage"],
            "matched_skills": detailed_match["matched_skills"],
            "missing_skills": detailed_match["missing_skills"],
        },
        "all_matches": [
            {
                "resume_id": m["resume_id"],
                "score": m["score"],
                "metadata": m.get("metadata", {})
            }
            for m in matches
        ],
        "generated_email": None,
        "generated_cover_letter": None
    }

    # Generate email if requested
    if payload.generate_email:
        try:
            email_result = await llm_generator.generate_application_email(
                jd_text=job.description,
                resume_context=rag_context,
                candidate_name=candidate_name,
                match_score=best_match["score"]
            )
            response_data["generated_email"] = email_result

            # Save to application record
            application = JobApplication(
                job_id=payload.job_id,
                resume_id=best_resume_id,
                similarity_score=best_match["score"],
                match_details=detailed_match,
                generated_subject=email_result.get("subject", ""),
                generated_email=email_result.get("body", ""),
                status="draft"
            )
            db.add(application)
            await db.commit()
            await db.refresh(application)
            response_data["application_id"] = application.id

        except ConnectionError as e:
            logger.warning(f"Ollama not available: {e}")
            response_data["generated_email"] = {
                "error": str(e),
                "subject": f"Application for {job.title or 'Position'}",
                "body": "Ollama is not running. Please start Ollama to generate emails."
            }

    # Generate cover letter if requested
    if payload.generate_cover_letter:
        try:
            cover_letter = await llm_generator.generate_cover_letter(
                jd_text=job.description,
                resume_context=rag_context,
                candidate_name=candidate_name
            )
            response_data["generated_cover_letter"] = cover_letter
        except Exception as e:
            logger.warning(f"Cover letter generation failed: {e}")
            response_data["generated_cover_letter"] = None

    return response_data


async def _process_jd(
    jd_text: str,
    db: AsyncSession,
    source: JobSource = JobSource.MANUAL,
    source_url: str = None,
    company: str = None,
    title: str = None
) -> dict:
    """Common JD processing: extract info, save to DB, embed"""
    # Extract structured info using LLM (with fallback)
    try:
        extracted = await llm_generator.extract_jd_info(jd_text)
    except Exception as e:
        logger.warning(f"LLM extraction failed, using fallback: {e}")
        extracted = llm_generator._fallback_jd_extraction(jd_text)

    job_id = str(uuid.uuid4())

    # Create DB record
    job = JobPosting(
        id=job_id,
        title=title or extracted.get("title", "Unknown Position"),
        company=company or extracted.get("company", ""),
        location=extracted.get("location", ""),
        job_type=extracted.get("job_type", ""),
        experience_level=extracted.get("experience_level", ""),
        description=jd_text,
        requirements=extracted.get("requirements", ""),
        skills_required=extracted.get("skills", []),
        technologies=extracted.get("technologies", []),
        source=source,
        source_url=source_url,
        contact_email=extracted.get("contact_email", ""),
        salary_range=extracted.get("salary_range", ""),
        is_embedded=False
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Embed the JD
    try:
        metadata = {
            "job_id": job_id,
            "title": job.title,
            "company": job.company or "",
        }
        vector_store.add_job_embedding(job_id, jd_text, metadata)

        # Mark as embedded
        await db.execute(
            update(JobPosting).where(JobPosting.id == job_id).values(is_embedded=True)
        )
        await db.commit()
    except Exception as e:
        logger.error(f"JD embedding failed: {e}")

    return {
        "id": job_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "skills_required": job.skills_required,
        "technologies": job.technologies,
        "contact_email": job.contact_email,
        "experience_level": job.experience_level,
        "is_embedded": True,
        "message": "Job description processed successfully"
    }


@router.get("/jobs", response_model=list)
async def list_jobs(db: AsyncSession = Depends(get_db)):
    """List all stored job postings"""
    result = await db.execute(
        select(JobPosting)
        .where(JobPosting.is_active == True)
        .order_by(JobPosting.created_at.desc())
        .limit(100)
    )
    jobs = result.scalars().all()

    return [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "source": j.source.value if j.source else "manual",
            "skills_required": j.skills_required or [],
            "is_embedded": j.is_embedded,
            "created_at": j.created_at.isoformat() if j.created_at else None
        }
        for j in jobs
    ]
