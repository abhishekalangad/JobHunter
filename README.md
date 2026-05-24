# 🤖 AI-Powered RAG-Based Automated Job Application System

A full-stack AI-powered recruitment automation platform that intelligently matches job descriptions with the most suitable resume using RAG, vector embeddings, semantic similarity, and local/open-source AI models.

## 🚀 Tech Stack

### Frontend
- Next.js 14 (App Router)
- Tailwind CSS
- shadcn/ui

### Backend
- FastAPI (Python)
- ChromaDB (Vector Store)
- sentence-transformers (Embeddings)
- LangChain
- Ollama (Local LLM - Mistral/Llama3)
- SQLite → PostgreSQL

### AI/NLP
- sentence-transformers/all-MiniLM-L6-v2
- EasyOCR
- pdfplumber / python-docx
- Playwright (web scraping)

### Email
- Gmail SMTP via yagmail

## 📁 Project Structure

```
Job_hunter/
├── frontend/          # Next.js frontend
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── main.py
│   │   ├── rag/       # RAG pipeline
│   │   ├── parser/    # Document parsers
│   │   ├── routes/    # API routes
│   │   ├── email/     # SMTP service
│   │   ├── scraper/   # Job scraping
│   │   └── database/  # DB models
│   ├── chroma_db/     # Vector DB storage
│   └── resumes/       # Uploaded resumes
└── docker-compose.yml
```

## 🛠️ Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Ollama installed locally

### Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Ollama Setup
```bash
ollama pull mistral
```

## 🎯 Features
- Multi-resume upload (PDF/DOCX)
- RAG-based resume-JD matching
- Semantic similarity scoring
- AI-generated personalized emails
- Job scraping from multiple platforms
- Application tracking dashboard
- Gmail SMTP integration
