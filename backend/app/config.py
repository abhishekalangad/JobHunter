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
    app_name: str = Field(default="AI Job Hunter")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=True)
    secret_key: str = Field(default="dev-secret-key")

    # Server
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001"
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./job_hunter.db"
    )

    # ChromaDB
    chroma_persist_dir: str = Field(default="./chroma_db")
    chroma_collection_resumes: str = Field(default="resumes")
    chroma_collection_jobs: str = Field(default="jobs")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.2")
    ollama_timeout: int = Field(default=120)

    # Gemini (Alternative to Ollama)
    gemini_api_key: str = Field(default="")

    # Embeddings
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2"
    )

    # File Storage
    resume_upload_dir: str = Field(default="./resumes")
    max_file_size_mb: int = Field(default=10)

    # Email
    gmail_user: str = Field(default="")
    gmail_app_password: str = Field(default="")
    email_from_name: str = Field(default="Job Application Bot")

    # RAG Settings
    chunk_size: int = Field(default=500)
    chunk_overlap: int = Field(default=50)
    top_k_results: int = Field(default=5)
    similarity_threshold: float = Field(default=0.6)

    # OCR
    ocr_language: str = Field(default="en")

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.resume_upload_dir, exist_ok=True)
os.makedirs(settings.chroma_persist_dir, exist_ok=True)
