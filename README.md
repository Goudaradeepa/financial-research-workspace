# Multi-Agent AI Financial Research & Analysis Workspace

An enterprise-grade **Multi-Agent AI Analysis System** designed for financial research, SEC filings ingestion (Form 10-K, 10-Q, Annual Reports), structured financial metric extraction, company-wise risk radar audit, and comparative market intelligence.

---

## Architecture & Milestone Roadmap

The system is structured and validated in three incremental, fully functional milestones:

```
[ PDF Upload / Ingestion ]
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ Milestone 1: Document Processing & FAISS Vector Engine │
│ • PyMuPDF High-fidelity text & page extraction         │
│ • Token-aware semantic chunking with page provenance   │
│ • all-MiniLM-L6-v2 embeddings + FAISS vector indexing  │
│ • SQLite metadata storage & Session management         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ Milestone 2: Extraction Agent & Validation Gate        │
│ • Document Relevance Gate (FINANCIAL/NON_FINANCIAL)   │
│ • Extraction Agent (Revenue, Net Income, EPS, EBITDA)  │
│ • Citation & Page-level audit provenance tracking      │
│ • Light-Themed Executive Workspace (React + Vite)      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ Milestone 3: Multi-Agent Analysis & LangGraph          │
│ • Red Flag Agent (Auditor qualifications & 7 risks)    │
│ • Research Agent (Multi-part question decomposition)   │
│ • Comparison Agent (Multi-company benchmark matrix)    │
│ • Report Agent (Synthesized executive briefing)        │
│ • LangGraph StateGraph Multi-Agent Orchestrator        │
└────────────────────────────────────────────────────────┘
```

---

## Milestones Overview

### Milestone 1: Document Processing & PDF Ingestion Pipeline
- **PyMuPDF Ingestion**: High-fidelity text extraction preserving page boundaries, headings, and tabular layouts.
- **Chunking Engine**: Semantic chunking preserving chunk index, character offsets, and page numbers.
- **FAISS Vector Indexing**: Dense vector index using `sentence-transformers/all-MiniLM-L6-v2` for low-latency semantic search.
- **Storage Layer**: SQLite schema managing research sessions, document statuses, chunks, and metadata.
- **Branch**: `milestone-1` | **Release Tag**: `v1.0-milestone1`

### Milestone 2: Extraction Agent & Document Relevance Validation Gate
- **Document Relevance Gate**: Lightweight validator analyzing terminology and context before extraction runs. Classifies filings into `FINANCIAL`, `NON_FINANCIAL`, and `UNCERTAIN` to prevent hallucinated metric tables on non-financial PDFs.
- **Extraction Agent**: Grounded extraction of key financial metrics (*Revenue*, *Net Income*, *Operating Margin*, *EBITDA*, *EPS*, *Free Cash Flow*, *Assets*, *Liabilities*) with verbatim text citation and page jump provenance.
- **Modern Light UI**: Polished, professional financial research interface with sidebar session switcher, drag-and-drop PDF dropzone, real-time agent status badges, and financial metrics inspector modal.
- **Branch**: `milestone-2` | **Release Tag**: `v2.0-milestone2`

### Milestone 3: Multi-Agent System & LangGraph Orchestration
- **Red Flag Agent**: Scans documents for 7 critical risk indicators (debt surges, declining margins, cash flow divergence, revenue deceleration, legal/regulatory risks, auditor qualifications).
- **Research Agent**: Multi-part query decomposition and iterative cited RAG retrieval across corporate filings.
- **Comparison Agent**: Side-by-side corporate benchmark comparing metrics across multiple companies.
- **Report Agent**: Generates structured executive briefings and synthesis reports.
- **LangGraph Multi-Agent Orchestration**: Orchestrated state machine (`StateGraph`) managing parallel and sequential agent invocation with full audit logging.
- **Branch**: `milestone-3` / `main` | **Release Tag**: `v3.0-milestone3`

---

## Technology Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn, SQLite3, PyMuPDF (fitz)
- **Vector Search & Embeddings**: FAISS (Facebook AI Similarity Search), Sentence-Transformers (`all-MiniLM-L6-v2`)
- **Multi-Agent Orchestration**: LangGraph (`StateGraph`), LangChain Core
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Lucide Icons
- **Testing**: Pytest, Pytest-Asyncio (26 comprehensive test suites)

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/Goudaradeepa/financial-research-workspace.git
cd financial-research-workspace

# Install Python dependencies
pip install -r requirements.txt
# (or install core packages: fastapi uvicorn pymupdf sentence-transformers faiss-cpu langgraph langchain-core pytest)

# Start the unified server
python run_server.py
```
The backend API and static frontend will be live at:
- **Workspace Web UI**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **FastAPI Interactive Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 3. Frontend Development (Optional)
```bash
cd frontend
npm install
npm run dev
```

### 4. Running Automated Tests
```bash
# Run complete test suite (26 passing tests)
python -m pytest tests/ -v

# Run Milestone 1 tests
python -m pytest tests/test_agents.py tests/test_sessions_and_docs.py -v

# Run Milestone 2 Document Relevance Validator tests
python -m pytest tests/test_document_validator.py -v

# Run Milestone 3 LangGraph Multi-Agent tests
python -m pytest tests/test_langgraph.py tests/test_next_milestone.py -v
```

---

## Git Milestone Branches & Tags

| Milestone | Git Branch | Git Tag | Description |
|---|---|---|---|
| **Milestone 1** | `milestone-1` | `v1.0-milestone1` | PDF Ingestion, Chunking, FAISS Indexing & SQLite Storage |
| **Milestone 2** | `milestone-2` | `v2.0-milestone2` | Extraction Agent, Document Relevance Gate & React UI |
| **Milestone 3** | `milestone-3` / `main` | `v3.0-milestone3` | LangGraph Multi-Agent Orchestration, Risk Radar & Synthesis |
