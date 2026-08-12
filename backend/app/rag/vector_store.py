"""
Vector Store Service - ChromaDB integration for resume & JD embeddings
Handles all CRUD operations on the vector database
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from app.config import settings
from app.rag.embeddings import embedding_service


class VectorStoreService:
    """Manages ChromaDB collections for resumes and job postings"""

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._initialize_client()

    def _initialize_client(self):
        """Initialize ChromaDB persistent client"""
        try:
            logger.info(f"🔄 Initializing ChromaDB at: {settings.chroma_persist_dir}")
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            # Initialize collections
            self._resume_collection = self._client.get_or_create_collection(
                name=settings.chroma_collection_resumes,
                metadata={"hnsw:space": "cosine"}
            )
            self._job_collection = self._client.get_or_create_collection(
                name=settings.chroma_collection_jobs,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("✅ ChromaDB initialized with resume and job collections")
        except Exception as e:
            logger.error(f"❌ ChromaDB initialization failed: {e}")
            raise

    @property
    def resume_collection(self):
        return self._resume_collection

    @property
    def job_collection(self):
        return self._job_collection

    # ─── Resume Operations ────────────────────────────────────────────────

    def add_resume_chunks(
        self,
        resume_id: str,
        chunks: List[str],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """
        Add resume text chunks to vector store.
        Each chunk gets its own embedding for granular retrieval.
        """
        if not chunks:
            logger.warning(f"No chunks provided for resume {resume_id}")
            return []

        chunk_ids = []
        embeddings = embedding_service.embed_batch(chunks)

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{resume_id}_chunk_{i}"
            chunk_metadata = {
                **metadata,
                "resume_id": resume_id,
                "chunk_index": i,
                "chunk_count": len(chunks)
            }

            self._resume_collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[chunk_metadata]
            )
            chunk_ids.append(chunk_id)

        logger.info(f"✅ Added {len(chunk_ids)} chunks for resume {resume_id}")
        return chunk_ids

    def search_resumes(
        self,
        query_text: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search resumes using semantic similarity.
        Returns ranked resume chunks with scores.
        """
        top_k = top_k or settings.top_k_results
        query_embedding = embedding_service.embed_text(query_text)

        where_clause = filter_metadata if filter_metadata else None

        results = self._resume_collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k * 3, self._resume_collection.count() or 1),
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )

        ids = results["ids"][0] if results["ids"] else []
        if not ids:
            return []

        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        # Process and deduplicate by resume_id (keep best chunk per resume)
        resume_scores = {}
        for doc_id, doc, meta, distance in zip(
            ids, documents, metadatas, distances
        ):
            resume_id = meta.get("resume_id", doc_id)
            # Convert distance to similarity (ChromaDB cosine distance: 0=identical)
            similarity = round((1 - distance) * 100, 2)

            if resume_id not in resume_scores or similarity > resume_scores[resume_id]["score"]:
                resume_scores[resume_id] = {
                    "resume_id": resume_id,
                    "score": similarity,
                    "best_chunk": doc,
                    "metadata": meta,
                    "chunk_id": doc_id
                }

        # Sort by score descending
        ranked = sorted(resume_scores.values(), key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]

    def get_resume_chunks(self, resume_id: str) -> List[Dict[str, Any]]:
        """Retrieve all chunks for a specific resume"""
        results = self._resume_collection.get(
            where={"resume_id": resume_id},
            include=["documents", "metadatas"]
        )
        chunks = []
        for doc_id, doc, meta in zip(
            results["ids"] or [],
            results["documents"] or [],
            results["metadatas"] or []
        ):
            chunks.append({"id": doc_id, "text": doc, "metadata": meta})
        return chunks

    def delete_resume(self, resume_id: str) -> bool:
        """Delete all chunks for a resume from vector store"""
        try:
            results = self._resume_collection.get(where={"resume_id": resume_id})
            if results["ids"]:
                self._resume_collection.delete(ids=results["ids"])
                logger.info(f"✅ Deleted {len(results['ids'])} chunks for resume {resume_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete resume {resume_id}: {e}")
            return False

    # ─── Job Operations ───────────────────────────────────────────────────

    def add_job_embedding(
        self,
        job_id: str,
        job_text: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Add a job posting embedding to vector store"""
        embedding = embedding_service.embed_text(job_text)

        self._job_collection.add(
            ids=[job_id],
            embeddings=[embedding],
            documents=[job_text],
            metadatas=[metadata]
        )
        logger.info(f"✅ Job embedding added: {job_id}")
        return job_id

    def search_jobs(
        self,
        query_text: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Search jobs using semantic similarity"""
        query_embedding = embedding_service.embed_text(query_text)

        count = self._job_collection.count()
        if count == 0:
            return []

        results = self._job_collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"]
        )

        jobs = []
        ids = results["ids"][0] if results["ids"] else []
        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []
        for doc_id, doc, meta, distance in zip(
            ids, documents, metadatas, distances
        ):
            jobs.append({
                "job_id": doc_id,
                "score": round((1 - distance) * 100, 2),
                "text": doc,
                "metadata": meta
            })

        return jobs

    def get_collection_stats(self) -> Dict[str, int]:
        """Get collection statistics"""
        return {
            "resume_chunks": self._resume_collection.count(),
            "job_postings": self._job_collection.count()
        }


# Singleton instance
vector_store = VectorStoreService()
