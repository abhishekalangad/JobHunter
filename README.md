# 🤖 AI Job Hunter — RAG-Powered Automated Job Application System

An intelligent, full-stack recruitment platform that automatically matches your resume library with job descriptions, scores how well you fit a role, and uses Artificial Intelligence (AI) powered by **Google Gemini API** to draft and send personalized job application emails for you.

---

## 💡 What is AI Job Hunter? (In Simple Terms)

Applying for jobs manually is exhausting and repetitive. Normally, you have to tailor your CV, write custom emails, and keep track of dozens of applications.

**AI Job Hunter automates this entire process:**
1. **Stores Your Resumes**: Upload all your resume variations (Sales, Software Development, Management, etc.).
2. **Reads Any Job Description**: Paste text, upload a PDF, upload a screenshot/image of a job ad, or paste a website link.
3. **Smart Matching**: The system uses **Retrieval-Augmented Generation (RAG)** to scan your resumes and calculate an exact match percentage for the job.
4. **Drafts Personalized Emails**: The **Google Gemini AI model** reads your matched resume context and writes a custom, professional email and cover letter highlighting your relevant experience.
5. **One-Click Send & Track**: Review the generated email, click "Send", and the app emails the recruiter via Gmail while tracking your application on a dashboard.

---

## 🛠️ Complete Technology Stack (Technologies Used & Why)

Here is the complete list of every single technology, library, framework, and tool used in this project, including **what it is**, **which version is used**, and **why it was chosen**.

---

### 🖥️ Frontend (User Interface - What You See in the Browser)

| Technology | Exact Version | What It Is | Why It Is Used in AI Job Hunter |
| :--- | :--- | :--- | :--- |
| **Next.js** | `16.2.6` | Modern React Framework by Vercel | Used as the foundation of the frontend web application. Provides super-fast page rendering and dynamic routing using the App Router. |
| **React** | `19.2.4` | JavaScript UI Library | Handles interactive components (buttons, input forms, modals, tabs) so the UI reacts smoothly without refreshing the page. |
| **TypeScript** | `^5.0` | Strongly Typed JavaScript | Adds static type checking to JavaScript, preventing bugs and ensuring code reliability across all components. |
| **Tailwind CSS** | `^4.0` | CSS Framework | Used for designing a futuristic, dark-mode visual interface with custom colors, glowing borders, and clean layouts. |
| **Framer Motion** | `^12.38.0` | Animation Library | Powers smooth page transitions, entrance animations, and interactive hover effects to make the app feel ultra-premium. |
| **Lucide React** | `^1.14.0` | Icon Library | Provides crisp, modern icons (briefcase, search, mail, checkmark, file icons) used throughout the dashboard and navigation. |
| **Recharts** | `^3.8.1` | Data Visualization Library | Renders application metrics and conversion success rates as visual charts on the dashboard. |
| **React Dropzone** | `^15.0.0` | Drag-and-Drop Uploader | Allows users to drag and drop resume files (PDF/DOCX) or job screenshots directly into the browser. |
| **React Hot Toast**| `^2.6.0` | Notification Toast Library | Shows real-time pop-up alerts (e.g. "Resume uploaded successfully!", "Email sent to recruiter!"). |
| **Radix UI** | `^1.1` | Unstyled UI Components | Provides accessible dialog windows, progress bars, and tab components that match our dark theme. |
| **Axios** | `^1.16.0` | HTTP Request Client | Sends API calls from the browser frontend to the Python backend server (e.g. sending file uploads, triggering AI matching). |

---

### ⚙️ Backend (The Server & Logic Behind the Scenes)

| Technology | Exact Version | What It Is | Why It Is Used in AI Job Hunter |
| :--- | :--- | :--- | :--- |
| **Python** | `3.10` / `3.11` | Programming Language | Chosen for its industry-standard support for AI, Machine Learning, Data Processing, and Web APIs. |
| **FastAPI** | `0.111.0` | Asynchronous Python Web Framework | Serves as the core REST API backend. It is extremely fast and natively supports asynchronous operations for file handling and AI processing. |
| **Uvicorn** | `0.29.0` | ASGI Web Server | The web server that runs FastAPI, handling incoming requests from the Next.js frontend on port `8000`. |
| **Pydantic** | `2.7.1` | Data Validation & Settings | Validates all incoming API request data and ensures environment configuration variables are formatted correctly. |
| **SQLAlchemy** | `2.0.30` | Database ORM (Object-Relational Mapper) | Allows Python code to read and write to the database using structured Python objects instead of raw SQL queries. |
| **aiosqlite** | `0.20.0` | Asynchronous SQLite Driver | Connects FastAPI asynchronously to the local SQLite database file (`job_hunter.db`) without blocking server performance. |
| **SQLite** | Standard DB | Lightweight File-Based Database | Stores job application history, resume metadata, tracked applications, and email status logs locally in `job_hunter.db`. |
| **Loguru** | `0.7.2` | Advanced Logging Library | Generates clean, color-coded terminal logs for tracking server events, AI execution times, and errors. |
| **Tenacity** | `8.3.0` | Automatic Retry Library | Automatically retries failed external API requests (e.g. network blips during email sending or AI requests). |

---

### 🧠 AI, RAG & Vector Engine Stack (The Smart Matching & Generation Engine)

| Technology | Exact Version | What It Is | Why It Is Used in AI Job Hunter |
| :--- | :--- | :--- | :--- |
| **Google Gemini API** | `gemini-2.5-flash` | Advanced Cloud Large Language Model (LLM) | **The Core AI Model for Generation**. Reads retrieved resume context and job requirements to generate custom cold emails and cover letters fast, lightweight, and with zero local storage footprint. |
| **ChromaDB** | `0.5.0` | Open-Source Vector Database | Stores resume text chunks converted into mathematical vectors. Allows instant "semantic search" to find which resume chunk best fits a job description. |
| **Sentence-Transformers**| `2.7.0` | Text Embedding Library | Converts raw text sentences into 384-dimensional numerical vectors using the `all-MiniLM-L6-v2` model. |
| **LangChain** | `0.2.1` | AI Orchestration Framework | Connects the vector search engine with the Gemini API to manage prompt templates, context retrieval, and structured JSON extraction. |
| **scikit-learn & NumPy** | `1.5.0` / `1.26.4` | Math & Data Analysis Libraries | Calculates Cosine Similarity math scores between job description vectors and resume vectors to produce match percentages (0% - 100%). |
| **PyTorch & Transformers**| `2.3.0` / `4.41.1` | Deep Learning Frameworks | The underlying AI infrastructure that powers local embedding vector calculations. |

---

### 📄 Document Processing, OCR & Web Extraction

| Technology | Exact Version | What It Is | Why It Is Used in AI Job Hunter |
| :--- | :--- | :--- | :--- |
| **pdfplumber & pypdf** | `0.11.0` / `4.2.0` | PDF Extraction Libraries | Reads and extracts clean text, bullet points, and contact info from PDF resumes and PDF job descriptions. |
| **python-docx** | `1.1.2` | Word Document Parser | Reads Microsoft Word (`.docx`) resume files uploaded by the user. |
| **EasyOCR** | `1.7.1` | Optical Character Recognition (OCR) | Reads text inside images. If a user uploads a screenshot of a job posting, EasyOCR extracts the text automatically. |
| **Pillow** | `10.3.0` | Python Image Processing Library | Used alongside EasyOCR to crop, resize, and convert uploaded image files for OCR processing. |
| **BeautifulSoup4 & lxml**| `4.12.3` / `5.2.2` | Web Scraping Libraries | If a user pastes a job URL link (e.g. a career page), BeautifulSoup parses the HTML webpage to extract the job title and requirements. |

---

### 📬 Email & Communication

| Technology | Exact Version | What It Is | Why It Is Used in AI Job Hunter |
| :--- | :--- | :--- | :--- |
| **Python smtplib & email.mime** | Native Standard | Built-in Python Email Services | Handles direct SMTP connection with Gmail servers to construct and send HTML emails with attached resume PDFs securely over TLS. |
| **secure-smtplib & yagmail** | `0.1.1` / `0.15.293` | Auxiliary Email Helpers | Backup utilities for managing SMTP authentication and header encoding. |

---

### ⚡ Single-Click Runner & Launch Tools

| Tool | File | Purpose |
| :--- | :--- | :--- |
| **`start.bat`** | [`start.bat`](file:///c:/Users/abhis/Desktop/Job_hunter/start.bat) | A custom Windows Batch script that checks dependencies, launches both Backend & Frontend in separate windows, and opens your web browser automatically with 1 double-click. |

---

## 🔄 How the RAG Pipeline Works (Step-by-Step)

```text
[ Resume File ] (PDF/DOCX)
       │
       ▼
1. Text Extraction ──► 2. Chunking & Vector Embedding (sentence-transformers)
                               │
                               ▼
                    [ ChromaDB Vector Store ]
                               ▲
                               │ 3. Vector Similarity Query
                               │
[ Job Description ] ───────────┴──► 4. Match Score & Context Retrieval
(Text / PDF / Image / URL)             │
                                       ▼
                            5. Gemini Prompt Construction (LangChain)
                                       │
                                       ▼
                            6. AI Generation (Google Gemini 2.5 Flash API)
                                       │
                                       ▼
                            [ Custom Email & Cover Letter ]
                                       │
                                       ▼
                            7. One-Click Gmail Dispatch (SMTP)
```

---

## 🚀 How to Run the Project

### Single-Click Launch

Simply double-click the **`start.bat`** file in the main project folder:

```text
C:\Users\abhis\Desktop\Job_hunter\start.bat
```

**What happens when you click it:**
- Opens **Window 1**: FastAPI Backend starting on `http://localhost:8000`
- Opens **Window 2**: Next.js Frontend starting on `http://localhost:3000`
- Opens your browser to **`http://localhost:3000`** automatically after 5 seconds!

---

## ⚙️ Environment Configuration (`.env`)

The backend configuration is managed via `backend/.env`:

```env
# Server Settings
API_HOST=0.0.0.0
API_PORT=8000

# Database & Vectors
DATABASE_URL=sqlite+aiosqlite:///./job_hunter.db
CHROMA_PERSIST_DIR=./chroma_db

# Google Gemini API (Active LLM Engine)
GEMINI_API_KEY=your_gemini_api_key_here

# Gmail SMTP Details
GMAIL_USER=abhishekalangad@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
EMAIL_FROM_NAME="Abhishek"
```

---

## 🌐 API Endpoint Summary

| Category | Endpoint | Method | What It Does |
| :--- | :--- | :--- | :--- |
| **Health** | `/health` | `GET` | Checks if Database, ChromaDB, Gemini API, and Gmail are working |
| **Stats** | `/api/v1/stats` | `GET` | Returns count of uploaded resumes, matched jobs, and sent emails |
| **Resumes** | `/api/v1/resumes/upload` | `POST` | Uploads and vector-embeds a new PDF/DOCX resume |
| **Resumes** | `/api/v1/resumes/` | `GET` | Retrieves all uploaded resumes |
| **JD Match** | `/api/v1/jd/text` | `POST` | Processes a plain text Job Description |
| **JD Match** | `/api/v1/jd/pdf` | `POST` | Extracts Job Description text from a PDF file |
| **JD Match** | `/api/v1/jd/image` | `POST` | Uses EasyOCR to read a Job Description from an image screenshot |
| **JD Match** | `/api/v1/jd/url` | `POST` | Scrapes Job Description content from a website link |
| **JD Match** | `/api/v1/jd/match` | `POST` | Performs RAG similarity search and generates Gemini AI email & cover letter |
| **Email** | `/api/v1/email/send` | `POST` | Sends generated application email via Gmail SMTP |
| **Email** | `/api/v1/email/applications`| `GET` | Fetches history of all tracked job applications |

---

## 📜 License

This project is open-source and available under the **MIT License**.
