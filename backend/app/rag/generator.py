"""
LLM Generator - Uses Ollama (local LLM) for email and cover letter generation
Implements RAG context injection into prompts
"""
import httpx
import json
from typing import Dict, Any, Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings


SYSTEM_PROMPT = """You are an expert job application writer. You help candidates craft 
professional, personalized, and compelling job application emails and cover letters.
Your writing is:
- Professional yet warm and human
- Specific to the job description and candidate's background
- ATS-optimized with relevant keywords
- Concise and impactful
- Free of generic AI-sounding phrases

Always use the provided resume context and job description to make the output highly specific.
Never hallucinate information not present in the resume context."""


EMAIL_GENERATION_PROMPT = """You are helping craft a job application email.

JOB DESCRIPTION:
{jd_text}

CANDIDATE RESUME CONTEXT:
{resume_context}

CANDIDATE NAME: {candidate_name}
SIMILARITY MATCH SCORE: {match_score}%

Generate a professional job application email with the following structure:
1. SUBJECT: A compelling subject line (start with "SUBJECT:")
2. EMAIL BODY: A complete professional email body

Requirements:
- Address the hiring manager professionally
- Mention the specific role from the JD
- Highlight 2-3 most relevant skills/projects from the resume that match the JD
- Keep it concise (under 300 words for the body)
- Include a professional closing
- Sound human and specific, NOT generic

Format your response as:
SUBJECT: [subject line here]

Dear Hiring Manager,

[email body here]

Best regards,
{candidate_name}"""


COVER_LETTER_PROMPT = """Generate a professional cover letter for this job application.

JOB DESCRIPTION:
{jd_text}

CANDIDATE RESUME CONTEXT:
{resume_context}

CANDIDATE NAME: {candidate_name}

Requirements:
- Professional letter format
- 3 paragraphs: Introduction, Why You're a Match, Call to Action
- Specific skills and achievements from resume
- Enthusiasm for the company/role
- ATS-optimized keywords from JD
- Under 350 words

Format as a complete cover letter."""


JD_EXTRACTION_PROMPT = """Extract structured information from this job description.

JOB DESCRIPTION:
{jd_text}

Extract and return ONLY valid JSON in this exact format:
{{
    "title": "job title",
    "company": "company name or empty string",
    "location": "location or empty string",
    "experience_level": "fresher/junior/mid/senior or empty",
    "job_type": "full-time/part-time/remote/internship or empty",
    "skills": ["skill1", "skill2", "skill3"],
    "technologies": ["tech1", "tech2"],
    "requirements": "key requirements as a single string",
    "contact_email": "email if found else empty string",
    "salary_range": "salary if mentioned else empty string"
}}

Return ONLY the JSON object, no other text."""


class LLMGeneratorService:
    """Generates emails, cover letters, and extracts JD info using local Ollama LLM"""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout
        self.gemini_key = settings.gemini_api_key

    async def _call_llm(self, prompt: str, system: str = None) -> str:
        """Route to Gemini if key is present, otherwise fallback to local Ollama"""
        if self.gemini_key:
            return await self._call_gemini(prompt, system)
        return await self._call_ollama(prompt, system)

    async def _call_gemini(self, prompt: str, system: str = None) -> str:
        """Make async request to Google Gemini API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                logger.error(f"Gemini API Error: {e}")
                raise ConnectionError(f"Gemini API failed: {str(e)}")

    async def _call_ollama(self, prompt: str, system: str = None) -> str:
        """Make async request to Ollama API"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or SYSTEM_PROMPT,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 1024
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "").strip()
            except httpx.ConnectError:
                raise ConnectionError(
                    "Cannot connect to Ollama. Please ensure Ollama is running: "
                    "`ollama serve` and model is pulled: `ollama pull mistral`"
                )
            except httpx.TimeoutException:
                raise TimeoutError(
                    f"Ollama request timed out after {self.timeout}s. "
                    "Try a smaller model or increase OLLAMA_TIMEOUT."
                )

    async def check_ollama_status(self) -> Dict[str, Any]:
        """Check if LLM backend is available"""
        if self.gemini_key:
            return {
                "running": True,
                "models": ["gemini-1.5-flash"],
                "target_model": "gemini-1.5-flash",
                "model_available": True,
                "provider": "Gemini API"
            }

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                return {
                    "running": True,
                    "models": model_names,
                    "target_model": self.model,
                    "model_available": any(
                        self.model in name for name in model_names
                    )
                }
            except Exception as e:
                return {"running": False, "error": str(e), "provider": "Ollama"}

    async def generate_application_email(
        self,
        jd_text: str,
        resume_context: str,
        candidate_name: str,
        match_score: float
    ) -> Dict[str, str]:
        """Generate professional application email using RAG context"""
        logger.info(f"🤖 Generating application email for {candidate_name}")

        prompt = EMAIL_GENERATION_PROMPT.format(
            jd_text=jd_text[:3000],  # Limit JD length
            resume_context=resume_context[:2000],
            candidate_name=candidate_name or "Applicant",
            match_score=match_score
        )

        raw_output = await self._call_llm(prompt)

        # Parse subject and body
        subject = ""
        body = raw_output

        if "SUBJECT:" in raw_output:
            lines = raw_output.split("\n")
            subject_line = next(
                (l for l in lines if l.strip().startswith("SUBJECT:")), ""
            )
            subject = subject_line.replace("SUBJECT:", "").strip()
            # Body is everything after the subject line
            body_start = raw_output.find("\n", raw_output.find("SUBJECT:"))
            body = raw_output[body_start:].strip()

        logger.info("✅ Email generated successfully")
        return {
            "subject": subject,
            "body": body,
            "raw": raw_output
        }

    async def generate_cover_letter(
        self,
        jd_text: str,
        resume_context: str,
        candidate_name: str
    ) -> str:
        """Generate a professional cover letter"""
        logger.info(f"🤖 Generating cover letter for {candidate_name}")

        prompt = COVER_LETTER_PROMPT.format(
            jd_text=jd_text[:3000],
            resume_context=resume_context[:2000],
            candidate_name=candidate_name or "Applicant"
        )

        cover_letter = await self._call_llm(prompt)
        logger.info("✅ Cover letter generated")
        return cover_letter

    async def extract_jd_info(self, jd_text: str) -> Dict[str, Any]:
        """Extract structured info from job description using LLM"""
        logger.info("🤖 Extracting JD information")

        prompt = JD_EXTRACTION_PROMPT.format(jd_text=jd_text[:4000])

        try:
            raw = await self._call_llm(
                prompt,
                system="You are a JSON extraction assistant. Return ONLY valid JSON, nothing else."
            )

            # Clean up response — sometimes LLMs add markdown fences
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip().rstrip("```")

            extracted = json.loads(raw)
            logger.info("✅ JD information extracted")
            return extracted

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ LLM returned invalid JSON: {e}. Using fallback extraction.")
            return self._fallback_jd_extraction(jd_text)

    def _fallback_jd_extraction(self, jd_text: str) -> Dict[str, Any]:
        """Basic keyword-based fallback when LLM fails"""
        import re

        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, jd_text)

        # Common tech skills
        tech_keywords = [
            "python", "java", "javascript", "react", "node.js", "sql", "mongodb",
            "aws", "docker", "kubernetes", "machine learning", "tensorflow",
            "django", "fastapi", "flask", "angular", "vue", "typescript",
            "c++", "c#", "golang", "rust", "php", "laravel"
        ]
        found_skills = [
            skill for skill in tech_keywords
            if skill.lower() in jd_text.lower()
        ]

        return {
            "title": "",
            "company": "",
            "location": "",
            "experience_level": "",
            "job_type": "",
            "skills": found_skills,
            "technologies": found_skills,
            "requirements": jd_text[:500],
            "contact_email": emails[0] if emails else "",
            "salary_range": ""
        }


# Singleton instance
llm_generator = LLMGeneratorService()
