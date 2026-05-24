"""
JD Parser - Extracts and processes job descriptions from multiple sources:
- Plain text
- PDF
- Image (OCR via EasyOCR)
- URL (web scraping)
"""
import re
import io
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import pdfplumber
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from app.config import settings


class JDParser:
    """Parses job descriptions from various input formats"""

    def __init__(self):
        self._ocr_reader = None  # Lazy load

    def _get_ocr_reader(self):
        """Lazy load EasyOCR to avoid startup overhead"""
        if self._ocr_reader is None:
            try:
                import easyocr
                logger.info("🔄 Loading EasyOCR model...")
                self._ocr_reader = easyocr.Reader([settings.ocr_language], gpu=False)
                logger.info("✅ EasyOCR loaded")
            except ImportError:
                raise ImportError("EasyOCR not installed. Run: pip install easyocr")
        return self._ocr_reader

    def parse_text(self, text: str) -> str:
        """Process plain text JD"""
        if not text or not text.strip():
            raise ValueError("JD text cannot be empty")
        return self._clean_text(text)

    def parse_pdf(self, file_path: str) -> str:
        """Extract text from PDF JD"""
        text_parts = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

            if not text_parts:
                raise ValueError("No text could be extracted from PDF")

            return self._clean_text("\n\n".join(text_parts))
        except Exception as e:
            logger.error(f"❌ PDF parsing failed: {e}")
            raise

    def parse_image(self, file_path: str) -> str:
        """Extract text from image using EasyOCR"""
        reader = self._get_ocr_reader()
        try:
            logger.info(f"🔍 Running OCR on: {file_path}")
            results = reader.readtext(file_path)

            # Sort by vertical position (top to bottom)
            results.sort(key=lambda x: x[0][0][1])

            text_parts = [result[1] for result in results if result[2] > 0.3]
            extracted = " ".join(text_parts)

            if not extracted.strip():
                raise ValueError("OCR could not extract text from image")

            logger.info(f"✅ OCR extracted {len(extracted)} characters")
            return self._clean_text(extracted)
        except Exception as e:
            logger.error(f"❌ OCR failed: {e}")
            raise

    async def parse_url(self, url: str) -> str:
        """Extract job description from a URL"""
        logger.info(f"🌐 Fetching JD from URL: {url}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers=headers
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                html_content = response.text

            text = self._extract_text_from_html(html_content, url)

            if not text or len(text.strip()) < 100:
                raise ValueError(
                    "Could not extract sufficient content from URL. "
                    "The page may require JavaScript or authentication."
                )

            logger.info(f"✅ Extracted {len(text)} characters from URL")
            return self._clean_text(text)

        except httpx.HTTPStatusError as e:
            raise ValueError(f"Failed to fetch URL (HTTP {e.response.status_code}): {url}")
        except httpx.ConnectError:
            raise ValueError(f"Cannot connect to URL: {url}")
        except Exception as e:
            logger.error(f"❌ URL parsing failed: {e}")
            raise

    def _extract_text_from_html(self, html: str, url: str = "") -> str:
        """Intelligently extract job content from HTML"""
        soup = BeautifulSoup(html, "lxml")

        # Remove noise elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header",
                                   "iframe", "noscript", "aside"]):
            tag.decompose()

        # Platform-specific selectors
        job_selectors = [
            # LinkedIn
            ".jobs-description__content",
            ".job-view-layout",
            # Indeed
            "#jobDescriptionText",
            ".jobsearch-JobComponent",
            # Glassdoor
            "[class*='JobDetails']",
            "[data-test='jobDescriptionContent']",
            # Naukri
            ".job-description",
            ".jd-header",
            # Generic
            "[class*='job-description']",
            "[class*='jobDescription']",
            "[id*='job-description']",
            "[id*='jobDescription']",
            "article",
            "main",
            ".content",
            "#content"
        ]

        for selector in job_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator="\n", strip=True)
                if len(text) > 200:
                    return text

        # Fallback: extract body text
        body = soup.find("body")
        if body:
            return body.get_text(separator="\n", strip=True)

        return soup.get_text(separator="\n", strip=True)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)

        # Remove common noise patterns
        text = re.sub(r'(Cookie|Privacy Policy|Terms of Service).*', '', text, flags=re.IGNORECASE)

        return text.strip()


class JDChunker:
    """Splits JD text for embedding"""

    def chunk(self, text: str, chunk_size: int = None, overlap: int = None) -> list:
        """Split JD text into overlapping chunks"""
        chunk_size = chunk_size or settings.chunk_size
        overlap = overlap or settings.chunk_overlap

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('. ')
                if last_period > chunk_size // 2:
                    end = start + last_period + 1
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - overlap

        return [c for c in chunks if c.strip()]


# Singleton instances
jd_parser = JDParser()
jd_chunker = JDChunker()
