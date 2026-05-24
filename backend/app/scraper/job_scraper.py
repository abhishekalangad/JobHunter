"""
Job Scraper Service - Fetches jobs from multiple platforms
Uses public APIs (Remotive, Adzuna) and lightweight web scraping
"""
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
from app.config import settings


class JobScraperService:
    """Aggregates jobs from multiple free/public sources"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; JobHunterBot/1.0)"
        }

    async def fetch_all(
        self,
        keywords: str,
        location: str = "India",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Fetch jobs from all available sources"""
        logger.info(f"🔍 Fetching jobs: '{keywords}' in '{location}'")

        tasks = [
            self._fetch_remotive(keywords, limit // 2),
            self._fetch_adzuna(keywords, location, limit // 2),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs = []
        for result in results:
            if isinstance(result, list):
                all_jobs.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Source failed: {result}")

        # Deduplicate by title+company
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            key = f"{job.get('title', '')}-{job.get('company', '')}"
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)

        logger.info(f"✅ Found {len(unique_jobs)} unique jobs")
        return unique_jobs[:limit]

    async def _fetch_remotive(self, keywords: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch remote jobs from Remotive API (free, no key needed)"""
        try:
            url = f"{settings.remotive_api_url}"
            params = {"search": keywords, "limit": limit}

            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            jobs = []
            for job in data.get("jobs", [])[:limit]:
                jobs.append({
                    "title": job.get("title", ""),
                    "company": job.get("company_name", ""),
                    "location": job.get("candidate_required_location", "Remote"),
                    "job_type": job.get("job_type", ""),
                    "description": job.get("description", ""),
                    "url": job.get("url", ""),
                    "salary_range": job.get("salary", ""),
                    "skills": [tag for tag in job.get("tags", [])],
                    "source": "remotive",
                    "posted_date": job.get("publication_date", "")
                })

            logger.info(f"✅ Remotive: {len(jobs)} jobs")
            return jobs

        except Exception as e:
            logger.warning(f"⚠️ Remotive fetch failed: {e}")
            return []

    async def _fetch_adzuna(
        self,
        keywords: str,
        location: str = "India",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch jobs from Adzuna API (free tier: 250 calls/month)"""
        if not settings.adzuna_app_id or not settings.adzuna_app_key:
            logger.info("Adzuna API keys not configured, skipping")
            return []

        try:
            # Map location to Adzuna country code
            country_map = {
                "india": "in", "us": "us", "uk": "gb",
                "canada": "ca", "australia": "au"
            }
            country = country_map.get(location.lower(), "in")

            url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
            params = {
                "app_id": settings.adzuna_app_id,
                "app_key": settings.adzuna_app_key,
                "what": keywords,
                "where": location,
                "results_per_page": limit,
                "content-type": "application/json"
            }

            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            jobs = []
            for job in data.get("results", [])[:limit]:
                jobs.append({
                    "title": job.get("title", ""),
                    "company": job.get("company", {}).get("display_name", ""),
                    "location": job.get("location", {}).get("display_name", ""),
                    "description": job.get("description", ""),
                    "url": job.get("redirect_url", ""),
                    "salary_range": f"{job.get('salary_min', '')} - {job.get('salary_max', '')}",
                    "source": "adzuna",
                    "posted_date": job.get("created", "")
                })

            logger.info(f"✅ Adzuna: {len(jobs)} jobs")
            return jobs

        except Exception as e:
            logger.warning(f"⚠️ Adzuna fetch failed: {e}")
            return []

    async def _fetch_github_jobs_alternative(
        self,
        keywords: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch from HN Who's Hiring and similar community boards"""
        # This is a placeholder for community-sourced job data
        return []

    async def fetch_from_career_page(self, company_url: str) -> List[Dict[str, Any]]:
        """
        Attempt to scrape jobs from a company's career page.
        Basic extraction - works for simple career pages.
        """
        try:
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                response = await client.get(company_url, headers=self.headers)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Look for job listings
            job_containers = (
                soup.find_all(class_=lambda x: x and "job" in x.lower()) or
                soup.find_all(class_=lambda x: x and "position" in x.lower()) or
                soup.find_all(class_=lambda x: x and "opening" in x.lower())
            )

            jobs = []
            for container in job_containers[:20]:
                title_el = container.find(["h1", "h2", "h3", "h4", "a"])
                jobs.append({
                    "title": title_el.get_text(strip=True) if title_el else "Position",
                    "company": company_url,
                    "description": container.get_text(strip=True)[:500],
                    "url": company_url,
                    "source": "career_page"
                })

            return jobs

        except Exception as e:
            logger.warning(f"Career page scrape failed for {company_url}: {e}")
            return []


# Singleton instance
job_scraper = JobScraperService()
