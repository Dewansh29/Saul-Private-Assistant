# ⚖️ Saul Goodman — AI Financial Strategy Assistant

> *"Better Call Saul... for your financials."*

**Saul Goodman** is an AI-powered financial analysis platform that reads your company's annual reports (PDF, Excel, CSV) and produces a full investment-grade memo — powered by a multi-agent debate system using **Google Gemini AI** and **LangGraph**.

Upload a financial document and watch three AI personas — an **Optimist CEO**, a **Realist CFO**, and a **Skeptic Investor** — debate the numbers and synthesize a final verdict.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite, TailwindCSS, Axios, React Router |
| **Backend** | Python, FastAPI, Uvicorn, Rag, Agentic ai |
| **AI Core** | Google Gemini 2.5 Flash Lite |
| **Orchestration** | LangGraph (multi-agent state machine) |
| **Data Processing** | Pandas, PyMuPDF, Camelot, OpenPyXL |
| **Report Export** | python-docx (Word `.docx` download) |

---

## 🤖 The AI Agent Pipeline

When you upload a document, a full pipeline of agents runs automatically:

```
Upload File
    ↓
Ingestion Agent  →  (PDF) TOC Agent → PDF Extractor → KPI Extractor
                 →  (Excel/CSV) Structured Data Agent
    ↓
Company Identifier Agent
    ↓
┌─────────────────────────────────────────┐
│  The Optimist (CEO)  — finds strengths  │
│  The Realist  (CFO)  — calculates ratios│
│  The Skeptic (Investor) — finds risks   │
└─────────────────────────────────────────┘
    ↓
Summary Agent → Investment Memo
    ↓
Scenario Agent  (What-if modeling)
Benchmark Agent (Industry comparison)
```

| Agent | Role |
|---|---|
| **Ingestion Agent** | Accepts PDF, Excel (.xlsx/.xls), and CSV files |
| **TOC Agent** | Reads the document's Table of Contents to find financial pages |
| **PDF Extraction Agent** | Pulls raw text and structured tables from key pages |
| **KPI Extraction Agent** | Extracts Revenue, Net Profit, Assets, Equity, and more |
| **Company Identifier Agent** | Detects the company name automatically |
| **Structured Data Agent** | Processes Excel/CSV financial data |
| **The Optimist (CEO)** | Argues the bull case with specific numbers |
| **The Realist (CFO)** | Computes ratios, spots areas to monitor |
| **The Skeptic (Investor)** | Finds red flags, risks, and missing data |
| **Summary Agent** | Synthesizes all three views into an investment memo |
| **Scenario Agent** | Runs "what-if" financial models based on your questions |
| **Benchmark Agent** | Compares company metrics against industry benchmarks |

---

## 🚀 Getting Started

### Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- A **Gemini API Key** — get one free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Dewansh29/Saul_Goodman-Financial-Assistant-.git
cd Saul_Goodman-Financial-Assistant-
```

---

### Step 2 — Set Up the Backend

```bash
cd backend
```

**Create and activate a Python virtual environment:**

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

**Install Python dependencies:**

```bash
pip install -r requirements.txt
```

**Create your `.env` file:**

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `backend/.env` and add your Gemini API key:

```
GEMINI_API_KEY="your_actual_gemini_api_key_here"
```

**Start the backend server:**

```bash
uvicorn main:app --reload
```

✅ Backend running at **http://localhost:8000**

---

### Step 3 — Set Up the Frontend

Open a **new terminal**, then:

```bash
cd frontend
npm install
npm run dev
```

✅ Frontend running at **http://localhost:5173**

---

### Step 4 — Open the App

Go to **[http://localhost:5173](http://localhost:5173)** in your browser.

> ⚠️ Both the backend (port 8000) and frontend (port 5173) must be running at the same time.

---

## 📁 Project Structure

```
Saul_Goodman-Financial-Assistant/
├── backend/
│   ├── .env.example        ← Copy to .env and add your Gemini API key
│   ├── requirements.txt    ← Python dependencies
│   ├── main.py             ← FastAPI routes (/analyze, /download_report, /scenario, /benchmark)
│   ├── agents.py           ← All LangGraph agent definitions
│   ├── utils.py            ← PDF/Excel extraction & Word report generation
│   └── template.docx       ← Word report template
└── frontend/
    ├── src/
    │   ├── components/     ← React UI components
    │   ├── App.jsx
    │   └── Router.jsx
    ├── package.json
    └── vite.config.js
```

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| Backend crashes on startup | Ensure `backend/.env` exists with a valid `GEMINI_API_KEY` |
| Frontend shows "Network Error" | Make sure the backend is running on port 8000 first |
| `pip install` fails | Activate your virtual environment first (look for `(.venv)` in terminal) |
| `npm install` fails | Check Node version: `node --version` (needs 18+) |
| Report download is empty | Ensure you ran `/analyze` first before downloading |
