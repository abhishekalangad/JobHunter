"""
Database Models - SQLAlchemy ORM definitions
"""
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Boolean,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum
import uuid


Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    DRAFT = "draft"
    SENT = "sent"
    REJECTED = "rejected"
    INTERVIEW = "interview"
    OFFER = "offer"
    WITHDRAWN = "withdrawn"


class JobSource(str, enum.Enum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    NAUKRI = "naukri"
    ADZUNA = "adzuna"
    REMOTIVE = "remotive"
    MANUAL = "manual"
    URL = "url"
    OTHER = "other"


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf, docx
    file_size = Column(Integer, nullable=False)

    # Parsed content
    full_text = Column(Text)
    name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    skills = Column(JSON, default=list)
    experience = Column(JSON, default=list)
    education = Column(JSON, default=list)
    projects = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    summary = Column(Text)

    # Vector store reference
    chroma_id = Column(String(255))
    is_embedded = Column(Boolean, default=False)

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    applications = relationship("JobApplication", back_populates="resume")


class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String(500), nullable=False)
    company = Column(String(255))
    location = Column(String(255))
    job_type = Column(String(100))  # full-time, part-time, remote
    experience_level = Column(String(100))
    salary_range = Column(String(200))

    # JD content
    description = Column(Text)
    requirements = Column(Text)
    skills_required = Column(JSON, default=list)
    technologies = Column(JSON, default=list)

    # Source
    source = Column(SAEnum(JobSource), default=JobSource.MANUAL)
    source_url = Column(String(1000))
    source_job_id = Column(String(255))
    contact_email = Column(String(255))

    # Vector store reference
    chroma_id = Column(String(255))
    is_embedded = Column(Boolean, default=False)

    # Metadata
    posted_date = Column(DateTime(timezone=True))
    deadline = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    applications = relationship("JobApplication", back_populates="job")


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(String, primary_key=True, default=generate_uuid)

    # Foreign Keys
    job_id = Column(String, ForeignKey("job_postings.id"), nullable=False)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)

    # Match data
    similarity_score = Column(Float)
    match_details = Column(JSON)  # skill matches, etc.

    # Generated content
    generated_subject = Column(String(500))
    generated_email = Column(Text)
    generated_cover_letter = Column(Text)

    # Status
    status = Column(SAEnum(ApplicationStatus), default=ApplicationStatus.DRAFT)

    # Email tracking
    email_sent_at = Column(DateTime(timezone=True))
    email_recipient = Column(String(255))

    # Notes
    notes = Column(Text)
    follow_up_date = Column(DateTime(timezone=True))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    job = relationship("JobPosting", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")
