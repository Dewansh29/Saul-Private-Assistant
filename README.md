# 🤖 DropShipping AI Assistant

A powerful AI-driven assistant that analyzes financial documents and provides actionable insights for dropshipping businesses. Powered by a multi-agent system using **Gemini AI** and **LangGraph**, it can process PDFs, Excel files, and CSVs to produce investment-grade financial memos.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite, TailwindCSS, Axios, React Router |
| **Backend** | Python, FastAPI, Uvicorn |
| **AI Core** | Google Gemini 2.0 Flash (via `google-generativeai`) |
| **Orchestration** | LangGraph |
| **Data Processing** | Pandas, PyMuPDF, Camelot |

---

## 🚀 Getting Started

Follow these steps **in order** to run the project locally.

### Prerequisites

Make sure you have these installed before proceeding:
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- A free **Gemini API Key** — get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/Dewansh29/DropShipping-Ai-Assistant.git
cd DropShipping-Ai-Assistant
```

---

### Step 2: Set Up the Backend

```bash
cd backend
```

**2a. Create and activate a Python virtual environment:**

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

**2b. Install Python dependencies:**

```bash
pip install -r requirements.txt
```

**2c. Create your `.env` file:**

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Now open `backend/.env` and replace the placeholder with your real Gemini API key:

```
GEMINI_API_KEY="your_actual_gemini_api_key_here"
```

**2d. Start the backend server:**

```bash
uvicorn main:app --reload
```

The backend will be running at **http://localhost:8000**

---

### Step 3: Set Up the Frontend

Open a **new terminal window** and navigate to the frontend folder:

```bash
cd frontend
```

**3a. Install Node dependencies:**

```bash
npm install
```

**3b. Start the frontend dev server:**

```bash
npm run dev
```

The frontend will be running at **http://localhost:5173**

---

### Step 4: Open the App

Open your browser and go to: **[http://localhost:5173](http://localhost:5173)**

> ⚠️ **Both the backend and frontend must be running at the same time** for the app to work.

---

## 🤖 AI Agents

The system uses a team of specialized AI agents:

| Agent | Role |
|---|---|
| **Ingestion Agent** | Handles PDF, Excel, and CSV file intake |
| **TOC Agent** | Parses document tables of contents |
| **PDF Extraction Agent** | Extracts raw text and tables from PDFs |
| **KPI Extraction Agent** | Identifies key financial performance indicators |
| **Company Identifier Agent** | Detects the target company name |
| **Structured Data Agent** | Processes Excel/CSV data |
| **The Optimist (CEO)** | Highlights strengths and growth potential |
| **The Realist (CFO)** | Provides pragmatic ratio analysis |
| **The Skeptic (Investor)** | Identifies red flags and risks |
| **Summary Agent** | Synthesizes all viewpoints into an investment memo |
| **Comprehensive Analysis Agent** | Deep dives into growth drivers and risks |
| **Scenario Agent** | "What-if" financial modeling |
| **Benchmark Agent** | Compares performance against industry benchmarks |

---

## 📁 Project Structure

```
DropShipping-Ai-Assistant/
├── backend/
│   ├── .env.example        # ← Copy this to .env and add your API key
│   ├── requirements.txt    # Python dependencies
│   ├── main.py             # FastAPI app & API routes
│   ├── agents.py           # LangGraph agent definitions
│   ├── utils.py            # Report generation utilities
│   └── template.docx       # Word report template
├── frontend/
│   ├── src/                # React source code
│   ├── package.json        # Node dependencies
│   └── vite.config.js      # Vite configuration
└── README.md
```

---

## ❓ Troubleshooting

**Backend crashes on startup?**
→ Make sure `backend/.env` exists and contains a valid `GEMINI_API_KEY`.

**Frontend shows "Network Error" or can't connect?**
→ Make sure the backend is running on port 8000 before starting the frontend.

**`pip install` fails?**
→ Make sure your virtual environment is activated (you should see `(.venv)` in your terminal prompt).

**`npm install` fails?**
→ Make sure you have Node.js 18+ installed: `node --version`
