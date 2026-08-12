"""
AI Job Hunter - FastAPI Main Application
Full-stack RAG-based job application automation system
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys
import os

from app.config import settings
from app.database.connection import init_db
from app.routes import resume_routes, jd_routes, email_routes


# ─── Configure Logging ────────────────────────────────────────────────────────
logger.remove()
os.makedirs("logs", exist_ok=True)
logger.add(
    sys.stderr,
    colorize=False,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}",
    level="INFO"
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    format="{time} | {level} | {name} | {message}"
)


# ─── Lifespan (startup/shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    logger.info("[START] Starting AI Job Hunter API...")
    logger.info(f"[INFO] Resume directory: {settings.resume_upload_dir}")
    logger.info(f"[INFO] ChromaDB: {settings.chroma_persist_dir}")
    logger.info(f"[INFO] LLM Model: {settings.ollama_model} @ {settings.ollama_base_url}")

    # Initialize database
    await init_db()

    # Check Ollama status
    from app.rag.generator import llm_generator
    ollama_status = await llm_generator.check_ollama_status()
    if ollama_status["running"]:
        if ollama_status.get("model_available"):
            logger.info(f"[OK] Ollama running with {settings.ollama_model}")
        else:
            logger.warning(
                f"[WARN] Ollama running but '{settings.ollama_model}' not found. "
                f"Available: {ollama_status.get('models', [])}. "
                f"Run: ollama pull {settings.ollama_model}"
            )
    else:
        logger.warning(
            "[WARN] Ollama is not running. Email generation will be unavailable. "
            "Start it with: ollama serve"
        )

    # Ensure directories exist
    os.makedirs("logs", exist_ok=True)
    os.makedirs(settings.resume_upload_dir, exist_ok=True)

    logger.info("[OK] AI Job Hunter API started successfully!")
    logger.info(f"[INFO] API Docs: http://{settings.api_host}:{settings.api_port}/docs")

    yield  # App runs here

    logger.info("[STOP] Shutting down AI Job Hunter API...")


# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Job Hunter API",
    description=(
        "🤖 AI-Powered RAG-Based Automated Job Application System\n\n"
        "Upload resumes, paste job descriptions, get semantic matching, "
        "generate personalized emails, and track applications."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ─── CORS Middleware ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(resume_routes.router, prefix="/api/v1")
app.include_router(jd_routes.router, prefix="/api/v1")
app.include_router(email_routes.router, prefix="/api/v1")


# ─── Root & Health Endpoints ─────────────────────────────────────────────────
@app.get("/", tags=["health"])
async def root():
    """API root - system info"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "features": [
            "Resume upload & embedding (RAG)",
            "JD parsing (text/PDF/image/URL)",
            "Semantic similarity matching",
            "AI email generation (Ollama)",
            "Gmail SMTP sending",
            "Job tracking dashboard",
            "Multi-platform job fetching"
        ]
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Comprehensive health check"""
    from app.rag.vector_store import vector_store
    from app.rag.generator import llm_generator
    from app.email.smtp_service import email_service

    # Vector store stats
    try:
        vs_stats = vector_store.get_collection_stats()
    except Exception as e:
        vs_stats = {"error": str(e)}

    # Ollama status
    ollama_status = await llm_generator.check_ollama_status()

    # Email status
    email_status = await email_service.test_connection()

    return {
        "status": "healthy",
        "database": "connected",
        "vector_store": vs_stats,
        "ollama": ollama_status,
        "email": email_status,
        "embedding_model": settings.embedding_model
    }


@app.get("/api/v1/stats", tags=["dashboard"])
async def get_stats(db=None):
    """Get dashboard statistics"""
    from app.rag.vector_store import vector_store
    from app.database.connection import AsyncSessionLocal
    from app.database.models import Resume, JobPosting, JobApplication
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as session:
        resume_count = await session.execute(
            select(func.count(Resume.id)).where(Resume.is_active == True)
        )
        job_count = await session.execute(
            select(func.count(JobPosting.id)).where(JobPosting.is_active == True)
        )
        app_count = await session.execute(
            select(func.count(JobApplication.id))
        )
        sent_count = await session.execute(
            select(func.count(JobApplication.id)).where(
                JobApplication.status == "sent"
            )
        )

    vs_stats = vector_store.get_collection_stats()

    return {
        "resumes": resume_count.scalar(),
        "jobs": job_count.scalar(),
        "applications": app_count.scalar(),
        "sent_applications": sent_count.scalar(),
        "resume_chunks_embedded": vs_stats.get("resume_chunks", 0),
        "jobs_embedded": vs_stats.get("job_postings", 0)
    }


# ─── Global Exception Handler ────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )
