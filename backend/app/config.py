"""
AI Job Hunter - Configuration Management
Centralized settings using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    # Application
    app_name: str = Field(default="AI Job Hunter", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=True, env="DEBUG")
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")

    # Server
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        env="ALLOWED_ORIGINS"
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./job_hunter.db",
        env="DATABASE_URL"
    )

    # ChromaDB
    chroma_persist_dir: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIR")
    chroma_collection_resumes: str = Field(default="resumes", env="CHROMA_COLLECTION_RESUMES")
    chroma_collection_jobs: str = Field(default="jobs", env="CHROMA_COLLECTION_JOBS")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", env="OLLAMA_MODEL")
    ollama_timeout: int = Field(default=120, env="OLLAMA_TIMEOUT")

    # Gemini (Alternative to Ollama)
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")

    # Embeddings
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL"
    )

    # File Storage
    resume_upload_dir: str = Field(default="./resumes", env="RESUME_UPLOAD_DIR")
    max_file_size_mb: int = Field(default=10, env="MAX_FILE_SIZE_MB")

    # Email
    gmail_user: str = Field(default="", env="GMAIL_USER")
    gmail_app_password: str = Field(default="", env="GMAIL_APP_PASSWORD")
    email_from_name: str = Field(default="Job Application Bot", env="EMAIL_FROM_NAME")

    # Job APIs
    adzuna_app_id: str = Field(default="", env="ADZUNA_APP_ID")
    adzuna_app_key: str = Field(default="", env="ADZUNA_APP_KEY")
    jsearch_api_key: str = Field(default="", env="JSEARCH_API_KEY")
    remotive_api_url: str = Field(
        default="https://remotive.com/api/remote-jobs",
        env="REMOTIVE_API_URL"
    )

    # RAG Settings
    chunk_size: int = Field(default=500, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
    top_k_results: int = Field(default=5, env="TOP_K_RESULTS")
    similarity_threshold: float = Field(default=0.6, env="SIMILARITY_THRESHOLD")

    # OCR
    ocr_language: str = Field(default="en", env="OCR_LANGUAGE")

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Singleton instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.resume_upload_dir, exist_ok=True)
os.makedirs(settings.chroma_persist_dir, exist_ok=True)
