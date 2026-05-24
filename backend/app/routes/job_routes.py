"""
Job Scraper Routes - API endpoints for fetching and searching jobs
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.database import get_db, JobPosting, JobSource
from app.scraper.job_scraper import job_scraper

router = APIRouter(prefix="/jobs", tags=["job-search"])


class JobSearchRequest(BaseModel):
    keywords: str
    location: Optional[str] = "India"
    limit: Optional[int] = 20
    save_to_db: Optional[bool] = True


class CareerPageRequest(BaseModel):
    url: str
    company_name: Optional[str] = None


@router.post("/search")
async def search_jobs(
    payload: JobSearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Search and fetch jobs from multiple platforms.
    Optionally save results to database for tracking.
    """
    jobs = await job_scraper.fetch_all(
        keywords=payload.keywords,
        location=payload.location,
        limit=payload.limit
    )

    if not jobs:
        return {
            "total": 0,
            "jobs": [],
            "message": "No jobs found. Try different keywords or check API keys."
        }

    saved_ids = []

    if payload.save_to_db:
        for job_data in jobs:
            # Map source string to enum
            source_map = {
                "remotive": JobSource.REMOTIVE,
                "adzuna": JobSource.ADZUNA,
                "career_page": JobSource.OTHER,
            }
            source = source_map.get(job_data.get("source", ""), JobSource.OTHER)

            # Check for duplicates (by title + company)
            existing = await db.execute(
                select(JobPosting).where(
                    JobPosting.title == job_data.get("title", ""),
                    JobPosting.company == job_data.get("company", "")
                )
            )
            if existing.scalar_one_or_none():
                continue

            job = JobPosting(
                title=job_data.get("title", "Unknown"),
                company=job_data.get("company", ""),
                location=job_data.get("location", ""),
                job_type=job_data.get("job_type", ""),
                description=job_data.get("description", ""),
                skills_required=job_data.get("skills", []),
                source=source,
                source_url=job_data.get("url", ""),
                salary_range=job_data.get("salary_range", "")
            )
            db.add(job)
            saved_ids.append(job.id)

        await db.commit()

    return {
        "total": len(jobs),
        "saved": len(saved_ids),
        "jobs": jobs
    }


@router.post("/career-page")
async def fetch_career_page(
    payload: CareerPageRequest,
    db: AsyncSession = Depends(get_db)
):
    """Fetch job listings from a company career page"""
    jobs = await job_scraper.fetch_from_career_page(payload.url)

    return {
        "total": len(jobs),
        "company": payload.company_name or payload.url,
        "jobs": jobs
    }


@router.get("/saved")
async def get_saved_jobs(
    source: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all saved job postings from the database"""
    query = select(JobPosting).where(JobPosting.is_active == True)

    if source:
        try:
            source_enum = JobSource(source)
            query = query.where(JobPosting.source == source_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid source: {source}")

    query = query.order_by(JobPosting.created_at.desc()).limit(100)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "source": j.source.value if j.source else "manual",
            "source_url": j.source_url,
            "skills_required": j.skills_required or [],
            "salary_range": j.salary_range,
            "is_embedded": j.is_embedded,
            "created_at": j.created_at.isoformat() if j.created_at else None
        }
        for j in jobs
    ]
