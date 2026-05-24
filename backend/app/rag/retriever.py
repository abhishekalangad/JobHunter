"""
RAG Retriever - Orchestrates semantic search and context assembly
Core of the RAG pipeline: retrieves best resume match for a given JD
"""
from typing import List, Dict, Any, Tuple, Optional
from loguru import logger
from app.rag.vector_store import vector_store
from app.rag.embeddings import embedding_service
from app.config import settings


class RetrieverService:
    """
    Retrieves the most relevant resume(s) for a given job description.
    Implements semantic search with context windowing for RAG.
    """

    def find_best_resume_match(
        self,
        jd_text: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find the best matching resumes for a job description.
        Returns ranked list with similarity scores and matched chunks.
        """
        if not jd_text or not jd_text.strip():
            raise ValueError("Job description text cannot be empty")

        logger.info(f"🔍 Searching for best resume match (top_k={top_k})")

        # Search vector store
        raw_results = vector_store.search_resumes(jd_text, top_k=top_k)

        if not raw_results:
            logger.warning("No resume matches found")
            return []

        # Enrich results with additional matching context
        enriched_results = []
        for result in raw_results:
            resume_id = result["resume_id"]

            # Get all chunks for context assembly
            all_chunks = vector_store.get_resume_chunks(resume_id)
            context_chunks = self._select_relevant_chunks(jd_text, all_chunks, top_n=5)

            enriched = {
                **result,
                "context_chunks": context_chunks,
                "full_context": "\n\n".join([c["text"] for c in context_chunks]),
                "chunk_count": len(all_chunks)
            }
            enriched_results.append(enriched)

        logger.info(
            f"✅ Found {len(enriched_results)} matches. "
            f"Best score: {enriched_results[0]['score']:.1f}%"
        )
        return enriched_results

    def _select_relevant_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """Select the most relevant chunks from a resume for context injection"""
        if not chunks:
            return []

        if len(chunks) <= top_n:
            return chunks

        # Score each chunk against the query
        query_emb = embedding_service.embed_text(query)
        scored_chunks = []

        for chunk in chunks:
            try:
                chunk_emb = embedding_service.embed_text(chunk["text"])
                score = embedding_service.compute_similarity(query_emb, chunk_emb)
                scored_chunks.append({**chunk, "relevance_score": score})
            except Exception as e:
                logger.warning(f"Could not score chunk: {e}")
                continue

        # Sort by relevance and return top N
        scored_chunks.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return scored_chunks[:top_n]

    def build_rag_context(
        self,
        jd_text: str,
        resume_match: Dict[str, Any],
        resume_db_data: Optional[Dict] = None
    ) -> str:
        """
        Build the full RAG context string for LLM injection.
        Combines resume chunks + structured data from DB.
        """
        context_parts = []

        # Add structured resume data if available
        if resume_db_data:
            structured_info = self._format_structured_resume(resume_db_data)
            if structured_info:
                context_parts.append("=== RESUME STRUCTURED DATA ===\n" + structured_info)

        # Add retrieved chunks
        if resume_match.get("full_context"):
            context_parts.append("=== RESUME CONTENT SECTIONS ===\n" + resume_match["full_context"])

        # Add match score context
        context_parts.append(
            f"=== MATCH CONTEXT ===\n"
            f"This resume has a {resume_match['score']:.1f}% semantic match with the job description."
        )

        return "\n\n".join(context_parts)

    def _format_structured_resume(self, resume_data: Dict) -> str:
        """Format structured resume fields for LLM context"""
        parts = []

        if resume_data.get("name"):
            parts.append(f"Candidate Name: {resume_data['name']}")
        if resume_data.get("email"):
            parts.append(f"Email: {resume_data['email']}")
        if resume_data.get("skills"):
            skills = resume_data["skills"]
            if isinstance(skills, list):
                parts.append(f"Skills: {', '.join(skills)}")
        if resume_data.get("experience"):
            exp = resume_data["experience"]
            if isinstance(exp, list) and exp:
                parts.append(f"Experience: {exp[0] if isinstance(exp[0], str) else str(exp[0])}")
        if resume_data.get("education"):
            edu = resume_data["education"]
            if isinstance(edu, list) and edu:
                parts.append(f"Education: {edu[0] if isinstance(edu[0], str) else str(edu[0])}")

        return "\n".join(parts)

    def compute_detailed_match(
        self,
        jd_skills: List[str],
        resume_skills: List[str],
        base_score: float
    ) -> Dict[str, Any]:
        """Compute detailed skill-level match analysis"""
        jd_skills_lower = [s.lower().strip() for s in jd_skills]
        resume_skills_lower = [s.lower().strip() for s in resume_skills]

        matched_skills = [s for s in jd_skills_lower if s in resume_skills_lower]
        missing_skills = [s for s in jd_skills_lower if s not in resume_skills_lower]
        extra_skills = [s for s in resume_skills_lower if s not in jd_skills_lower]

        skill_match_pct = (
            len(matched_skills) / len(jd_skills_lower) * 100
            if jd_skills_lower else 0
        )

        return {
            "semantic_score": base_score,
            "skill_match_percentage": round(skill_match_pct, 1),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "bonus_skills": extra_skills[:10],
            "overall_score": round((base_score * 0.7 + skill_match_pct * 0.3), 2)
        }


# Singleton instance
retriever_service = RetrieverService()
