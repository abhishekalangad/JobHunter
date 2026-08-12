# pyrefly: ignore-all-errors
"""
LLM Generator - Uses Gemini API / Ollama (local LLM) for email, selection, and cover letter generation.
Implements technical recruiter RAG matching and concise recruiter-grade email application writing.
"""
import httpx
import json
from typing import Dict, Any, Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings


SYSTEM_PROMPT = """You are an expert technical recruiter and professional job application writer. You help software engineers craft highly tailored, concise, recruiter-friendly job application emails and cover letters.
Your writing is:
- Concise, professional, human, and direct (110-140 words for emails)
- Tailored specifically to the job description requirements and the candidate's actual engineering experience
- Highlights developer internship experience, practical engineering, REST API development, database optimization, and cloud services
- ATS-optimized without keyword stuffing or generic AI openings
- Strictly honest — never claims unheld skills or experience

Always rely on the candidate's actual technical accomplishments and the job description."""


RESUME_SELECTION_PROMPT = """
You are an expert technical recruiter and resume-matching engine.

Your task is to determine which candidate resume is the BEST MATCH for the
provided job description.

You may receive multiple candidate resumes. Do not assume that the first resume
is the correct one.

==================================================
JOB DESCRIPTION
==================================================

{jd_text}

==================================================
AVAILABLE RESUMES
==================================================

{resumes}

Each resume has a unique resume_id.

==================================================
MATCHING INSTRUCTIONS
==================================================

Analyze every resume against the job description.

Evaluate the following dynamically based on what the JD actually requires:

1. Core technical skills
2. Programming languages
3. Frameworks and libraries
4. Databases
5. Cloud/platform technologies
6. Tools and development technologies
7. Job responsibilities
8. Years/type of experience
9. Relevant internship or professional experience
10. Relevant projects
11. Domain knowledge
12. Education requirements
13. Certifications where relevant
14. Other important requirements explicitly mentioned in the JD

Do NOT use a fixed list of technologies.

The JD itself determines what is important.

==================================================
MATCH CLASSIFICATION
==================================================

For each important JD requirement, classify the candidate's evidence as:

STRONG_MATCH:
The resume demonstrates direct practical experience.

PARTIAL_MATCH:
The resume contains related experience, project exposure, coursework,
knowledge, or transferable skills, but not strong direct experience.

SKILL_ONLY:
The technology/skill is listed in the resume but there is little or no
evidence of practical usage.

MISSING:
There is no evidence in the resume.

Do not treat a skill appearing in a Skills section as equivalent to professional
experience.

==================================================
IMPORTANT RULE FOR MISSING SKILLS
==================================================

Missing JD requirements must NOT automatically make the candidate unsuitable.

Determine whether the missing requirement is:

- critical to the role
- preferred/nice-to-have
- learnable/adjacent to existing skills

If the candidate has related technical experience, identify whether the
candidate could reasonably position it as an area they are currently developing
or willing to learn.

NEVER claim that the candidate already knows a missing technology.

==================================================
SCORING
==================================================

Calculate a practical match score based primarily on:

- Direct technical matches
- Relevant professional/internship experience
- Relevant responsibilities
- Relevant projects
- Domain alignment
- Education/experience requirements

Do not give a high score simply because many generic keywords appear.

Prioritize evidence quality over keyword quantity.

==================================================
OUTPUT
==================================================

Return ONLY valid JSON in this format:

{{
    "selected_resume_id": "",
    "overall_match_score": 0,
    "selection_reason": "",
    "strong_matches": [
        {{
            "jd_requirement": "",
            "resume_evidence": "",
            "evidence_type": "experience/project/skill"
        }}
    ],
    "partial_matches": [
        {{
            "jd_requirement": "",
            "resume_evidence": "",
            "reason": ""
        }}
    ],
    "missing_requirements": [
        {{
            "jd_requirement": "",
            "importance": "critical/preferred/other",
            "related_candidate_skill": "",
            "learning_position_possible": true
        }}
    ],
    "best_experience": [],
    "best_projects": [],
    "keywords_to_use": [],
    "keywords_to_avoid_claiming": []
}}

Select exactly ONE best resume.
"""


EMAIL_GENERATION_PROMPT = """
You are an expert technical recruiter and professional job application writer.

Your task is to generate a concise, highly personalized application email for
the candidate using the JOB DESCRIPTION, the SELECTED RESUME, and the MATCH
ANALYSIS.

The email must sound like it was written specifically for this job, not like a
generic resume submission.

==================================================
JOB DESCRIPTION
==================================================

{jd_text}

==================================================
SELECTED RESUME
==================================================

{resume_context}

==================================================
MATCH ANALYSIS
==================================================

{match_analysis}

==================================================
CANDIDATE INFORMATION
==================================================

Name: {candidate_name}
Phone: {candidate_phone}
LinkedIn: {candidate_linkedin}
Portfolio: {candidate_portfolio}

==================================================
PRIMARY OBJECTIVE
==================================================

Write an email that makes a recruiter quickly understand:

1. Which role the candidate is applying for.
2. Why the candidate is technically relevant.
3. Which specific JD requirements are supported by the resume.
4. Which important adjacent areas the candidate can develop, when appropriate.
5. Why the recruiter should review the attached resume.

Do NOT reproduce the resume.

Do NOT reproduce the JD.

Select only the most valuable information from both.

==================================================
CONTENT STRATEGY
==================================================

The email should contain approximately 110–140 words excluding the signature.

Use the available resume and JD dynamically.

Do NOT hardcode or assume any specific programming language, framework,
database, cloud platform, role, company, or technology.

The technologies mentioned in the final email must come from the actual JD,
resume, or verified match analysis.

Prioritize:

1. Strong technical matches
2. Relevant professional/internship experience
3. Relevant project experience
4. Important JD keywords
5. Closely related skills that demonstrate transferability

Include approximately 4–6 relevant technical keywords naturally.

Do not keyword-stuff.

==================================================
OPENING
==================================================

Start directly with the application.

Mention:

- Exact job title
- Company name, if available
- One concise statement establishing the candidate's strongest relevant
  technical background

Avoid generic openings such as:

"I am writing to express my keen interest..."

"I am excited to apply..."

"I believe I am the perfect candidate..."

Instead, make the opening specific to the role.

==================================================
TECHNICAL MATCH SECTION
==================================================

Use 2 or 3 short bullet points.

Each bullet should follow this principle:

JD REQUIREMENT
+
RESUME EVIDENCE
+
RELEVANCE

For example, conceptually:

"Python/Django: Developed backend modules and REST APIs during a developer
internship, directly aligning with the role's backend requirements."

But NEVER reuse this example unless the actual JD and resume contain those
technologies.

The bullets must be generated dynamically from the strongest matches.

==================================================
MISSING JD REQUIREMENTS
==================================================

If the JD contains an important technology or requirement that is NOT present
in the resume:

DO NOT falsely claim experience.

Do not create a separate "gaps" section in the email.

If appropriate, mention ONE relevant missing area naturally as a learning or
development area, but ONLY when the match analysis indicates that this is
reasonable.

Examples of acceptable positioning:

"Alongside my existing backend experience, I am currently strengthening my
knowledge of [JD technology]."

"I am also keen to develop further expertise in [JD technology], building on
my existing experience with [related technology]."

"I am comfortable expanding into [JD technology] given my existing experience
with [related technology]."

Only use such language when supported by the candidate's background.

If there are no suitable missing skills to mention, do not mention gaps.

Never say:

"I have experience in [missing technology]."

==================================================
EXPERIENCE POSITIONING
==================================================

If the candidate has internships or professional experience:

Focus on practical engineering work.

Do not repeatedly describe the candidate as a "fresher."

Do not hide their early-career status either.

Position them naturally as an early-career software professional with practical
development experience.

If the candidate has no professional experience, use relevant projects,
education, certifications, and demonstrated technical skills instead.

==================================================
PROJECTS
==================================================

Mention a project ONLY when it provides strong evidence for a JD requirement.

Do not list multiple projects.

Do not explain a project in detail.

Use the project as evidence for relevance.

==================================================
STYLE
==================================================

The email must be:

- Concise
- Professional
- Human
- Specific
- Confident
- Technically credible
- Recruiter-friendly

Avoid:

- Generic AI language
- Excessive adjectives
- Long paragraphs
- Resume repetition
- Keyword stuffing
- Unverified claims
- Salary discussion
- Match score
- Excessive discussion of education
- Excessive discussion of being a fresher

==================================================
SUBJECT
==================================================

Use:

Application for [Exact Job Title] - [Candidate Name]

If the company/job title has a particularly useful identifier such as a job
code, include it only if it appears in the JD.

==================================================
FINAL FORMAT
==================================================

SUBJECT: Application for [Exact Job Title] - {candidate_name}

Dear Hiring Manager,

[2 concise sentences]

• [Dynamic JD/resume match]
• [Dynamic JD/resume match]
• [Optional third match only if genuinely valuable]

[1 concise closing sentence requesting an opportunity to discuss the role.]

Best regards,
{candidate_name}
Phone: {candidate_phone}
LinkedIn: {candidate_linkedin}
Portfolio: {candidate_portfolio}

==================================================
FINAL VALIDATION
==================================================

Before returning the email, verify:

- Exact job title is correct.
- Company name is correct if available.
- Selected resume is actually the best match.
- Every technical keyword is supported by JD/resume evidence.
- No missing technology is falsely claimed.
- Important JD keywords are naturally included.
- Only the strongest 4–6 keywords are used.
- At least one bullet references actual experience/project evidence.
- Email body is approximately 110–140 words.
- No unnecessary resume information.
- No generic AI opening.
- No match score.
- No hallucinated achievements.
- No unnecessary explanation of gaps.
- Signature is complete.

Return ONLY the final email.
"""


COVER_LETTER_PROMPT = """Generate a professional cover letter for this software engineering position.

JOB DESCRIPTION:
{jd_text}

CANDIDATE RESUME CONTEXT:
{resume_context}

CANDIDATE NAME: {candidate_name}
CANDIDATE PHONE: {candidate_phone}
CANDIDATE LINKEDIN: {candidate_linkedin}
CANDIDATE PORTFOLIO: {candidate_portfolio}

Requirements:
- Professional cover letter format starting with applicant contact header
- Focus on practical developer internship accomplishments, software development experience, REST API architecture, database management (MySQL), cloud integration (Firebase), and full-stack web capabilities (Python, Django/Flask, React).
- DO NOT focus on fresh graduate status. Highlight engineering execution, project deployments, and technical matching.
- 3 clear paragraphs: Introduction (role + company match), Core Technical Qualifications & Internship Accomplishments (mirror exact JD tech keywords), and Closing / Call to Action.
- ATS-optimized: embed exact technical keywords from the JD naturally throughout.
- Word count under 300 words.
- End with full sign-off and contact block.

Format as a complete cover letter ending with:

Sincerely,
{candidate_name}
{candidate_phone}
{candidate_linkedin}
{candidate_portfolio}"""


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
    """Generates emails, cover letters, and evaluates resumes using Gemini API or local Ollama LLM"""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout
        self.gemini_key = settings.gemini_api_key

    async def _call_llm(self, prompt: str, system: Optional[str] = None) -> str:
        """Route to Gemini if key is present, fallback to local Ollama if available"""
        if self.gemini_key:
            try:
                return await self._call_gemini(prompt, system)
            except Exception as e:
                logger.warning(f"⚠️ Gemini API failed ({e}). Attempting fallback to local Ollama...")
                try:
                    return await self._call_ollama(prompt, system)
                except Exception as ollama_err:
                    logger.error(f"Both Gemini and Ollama failed: {e} | {ollama_err}")
                    raise ConnectionError(f"Gemini API rate-limited and Ollama unavailable. ({e})")
        return await self._call_ollama(prompt, system)

    async def _call_gemini(self, prompt: str, system: Optional[str] = None) -> str:
        """Make async request to Google Gemini API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except httpx.ConnectError as e:
                logger.error(f"Gemini ConnectError: {e}")
                raise ConnectionError(f"Cannot reach Gemini API — check internet connection. ({e})")
            except httpx.HTTPStatusError as e:
                logger.error(f"Gemini HTTP {e.response.status_code}: {e.response.text[:300]}")
                raise ConnectionError(f"Gemini API error {e.response.status_code}: {e.response.text[:200]}")
            except Exception as e:
                logger.error(f"Gemini API Error [{type(e).__name__}]: {e}")
                raise ConnectionError(f"Gemini API failed [{type(e).__name__}]: {str(e)}")

    async def _call_ollama(self, prompt: str, system: Optional[str] = None) -> str:
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
                    "AI generation unavailable. Please check GEMINI_API_KEY in .env or ensure local LLM is running."
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
                "models": ["gemini-2.5-flash"],
                "target_model": "gemini-2.5-flash",
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

    async def select_best_resume(
        self,
        jd_text: str,
        resumes_text: str
    ) -> Dict[str, Any]:
        """Select best candidate resume and return detailed match classification JSON"""
        logger.info("🤖 Evaluating resumes with RESUME_SELECTION_PROMPT")

        prompt = RESUME_SELECTION_PROMPT.format(
            jd_text=jd_text[:4000],
            resumes=resumes_text[:8000]
        )

        try:
            raw = await self._call_llm(
                prompt,
                system="You are a technical recruiter matching engine. Return ONLY valid JSON, nothing else."
            )
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip().rstrip("```")
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"⚠️ Resume selection LLM call failed ({e}). Returning fallback selection structure.")
            return {
                "selected_resume_id": "",
                "overall_match_score": 75,
                "selection_reason": "Evaluated based on primary technical background.",
                "strong_matches": [],
                "partial_matches": [],
                "missing_requirements": [],
                "keywords_to_use": [],
                "keywords_to_avoid_claiming": []
            }

    def _fallback_application_email(
        self,
        jd_text: str,
        resume_context: str,
        candidate_name: str,
        candidate_phone: str = "+91-8606243568",
        candidate_linkedin: str = "https://www.linkedin.com/in/abhishek-kulangara/",
        candidate_portfolio: str = "https://abhishek-k-portfolio.vercel.app/"
    ) -> Dict[str, str]:
        """Generate a concise, professional recruiter-grade application email fallback (110-140 words)"""
        name = candidate_name or "ABHISHEK K"
        role_title = "Software Engineer"

        lines = [l.strip() for l in jd_text.split('\n') if l.strip()]
        for line in lines[:8]:
            if any(k in line for k in ["Engineer", "Developer", "Analyst", "Architect", "Role", "Position"]):
                cleaned = line.replace("Role:", "").replace("Position:", "").strip()
                if len(cleaned) < 50:
                    role_title = cleaned
                break

        subject = f"Application for {role_title} - {name}"
        body = (
            f"Dear Hiring Manager,\n\n"
            f"I am applying for the {role_title} position, bringing practical software engineering experience with a solid foundation in backend API development, database architecture, and full-stack web applications.\n\n"
            f"• Python & RESTful APIs: Developed backend modules and REST APIs during my developer internship, directly supporting core application services.\n"
            f"• MySQL & Database Engineering: Architected relational schemas and optimized SQL queries for high performance and data accuracy.\n"
            f"• Cloud & Modern Web Stack: Integrated Firebase cloud services and built responsive web interfaces with React.js.\n\n"
            f"I welcome the opportunity to discuss how my technical experience aligns with your team's engineering goals.\n\n"
            f"Best regards,\n"
            f"{name}\n"
            f"Phone: {candidate_phone}\n"
            f"LinkedIn: {candidate_linkedin}\n"
            f"Portfolio: {candidate_portfolio}"
        )

        return {
            "subject": subject,
            "body": body,
            "raw": body
        }

    def _fallback_cover_letter(
        self,
        jd_text: str,
        candidate_name: str,
        candidate_phone: str = "+91-8606243568",
        candidate_linkedin: str = "https://www.linkedin.com/in/abhishek-kulangara/",
        candidate_portfolio: str = "https://abhishek-k-portfolio.vercel.app/"
    ) -> str:
        """Fallback cover letter when LLMs are rate-limited or offline"""
        name = candidate_name or "ABHISHEK K"
        return (
            f"{name}\n"
            f"Phone: {candidate_phone}\n"
            f"LinkedIn: {candidate_linkedin}\n"
            f"Portfolio: {candidate_portfolio}\n\n"
            f"Dear Hiring Manager,\n\n"
            f"I am writing to express my strong interest in the Software Engineer position. With hands-on developer internship experience, "
            f"production software customization, and full-stack backend development skills, I am eager to contribute to your engineering goals.\n\n"
            f"My practical background includes engineering backend RESTful APIs with Python (Django, Flask), optimizing relational databases using MySQL, "
            f"and deploying modern cloud-connected interfaces. During my developer internship, I participated in UAT testing, module integration, and live client deployments.\n\n"
            f"I welcome the opportunity to discuss how my software development skills align with your team's needs.\n\n"
            f"Sincerely,\n"
            f"{name}"
        )

    async def generate_application_email(
        self,
        jd_text: str,
        resume_context: str,
        candidate_name: str,
        match_score: float = 0.0,
        match_analysis: Optional[str] = None,
        candidate_phone: str = "+91-8606243568",
        candidate_linkedin: str = "https://www.linkedin.com/in/abhishek-kulangara/",
        candidate_portfolio: str = "https://abhishek-k-portfolio.vercel.app/"
    ) -> Dict[str, str]:
        """Generate professional application email using RAG context and recruiter prompts"""
        logger.info(f"🤖 Generating application email for {candidate_name}")

        prompt = EMAIL_GENERATION_PROMPT.format(
            jd_text=jd_text[:3000],
            resume_context=resume_context[:2000],
            match_analysis=match_analysis or "High technical match based on backend engineering, database management, and cloud application experience.",
            candidate_name=candidate_name or "ABHISHEK K",
            candidate_phone=candidate_phone,
            candidate_linkedin=candidate_linkedin,
            candidate_portfolio=candidate_portfolio
        )

        try:
            raw_output = await self._call_llm(prompt)
        except Exception as e:
            logger.warning(f"⚠️ LLM generation failed ({e}). Utilizing smart RAG fallback email generator.")
            return self._fallback_application_email(
                jd_text, resume_context, candidate_name, candidate_phone, candidate_linkedin, candidate_portfolio
            )

        # Parse subject and body
        subject = ""
        body = raw_output

        if "SUBJECT:" in raw_output:
            lines = raw_output.split("\n")
            subject_line = next(
                (l for l in lines if l.strip().startswith("SUBJECT:")), ""
            )
            subject = subject_line.replace("SUBJECT:", "").strip()
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
        candidate_name: str,
        candidate_phone: str = "+91-8606243568",
        candidate_linkedin: str = "https://www.linkedin.com/in/abhishek-kulangara/",
        candidate_portfolio: str = "https://abhishek-k-portfolio.vercel.app/"
    ) -> str:
        """Generate a professional cover letter"""
        logger.info(f"🤖 Generating cover letter for {candidate_name}")

        prompt = COVER_LETTER_PROMPT.format(
            jd_text=jd_text[:3000],
            resume_context=resume_context[:2000],
            candidate_name=candidate_name or "ABHISHEK K",
            candidate_phone=candidate_phone,
            candidate_linkedin=candidate_linkedin,
            candidate_portfolio=candidate_portfolio
        )

        try:
            cover_letter = await self._call_llm(prompt)
            logger.info("✅ Cover letter generated")
            return cover_letter
        except Exception as e:
            logger.warning(f"⚠️ LLM cover letter generation failed ({e}). Utilizing smart fallback cover letter.")
            return self._fallback_cover_letter(
                jd_text, candidate_name, candidate_phone, candidate_linkedin, candidate_portfolio
            )

    async def extract_jd_info(self, jd_text: str) -> Dict[str, Any]:
        """Extract structured info from job description using LLM"""
        logger.info("🤖 Extracting JD information")

        prompt = JD_EXTRACTION_PROMPT.format(jd_text=jd_text[:4000])

        try:
            raw = await self._call_llm(
                prompt,
                system="You are a JSON extraction assistant. Return ONLY valid JSON, nothing else."
            )

            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip().rstrip("```")

            extracted = json.loads(raw)
            logger.info("✅ JD information extracted")
            return extracted

        except Exception as e:
            logger.warning(f"⚠️ LLM returned invalid JSON: {e}. Using fallback extraction.")
            return self._fallback_jd_extraction(jd_text)

    def _fallback_jd_extraction(self, jd_text: str) -> Dict[str, Any]:
        """Basic keyword-based fallback when LLM fails"""
        import re

        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, jd_text)

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
