import os
import sys
from pathlib import Path

# Add backend directory to sys.path so imports work smoothly
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db, DB_PATH
from routes.sessions import router as sessions_router
from routes.documents import router as documents_router
from routes.red_flags import router as red_flags_router
from routes.chat import router as chat_router
from seed_data import seed_flagship_annual_reports

# Initialize database tables
init_db()

# Ensure seed company annual reports are pre-loaded and indexed
try:
    seed_flagship_annual_reports()
except Exception as e:
    print(f"[Startup] Seed initialization info: {e}")

app = FastAPI(
    title="Financial Research Workspace API",
    description="Backend API for Multi-Agent Financial Research System (Document Agent, Extraction Agent, Red Flag Agent, Research Agent, Comparison Agent, Report Agent, and Orchestrator)",
    version="3.0.0"
)

# CORS configuration for development & preview
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(sessions_router)
app.include_router(documents_router)
app.include_router(red_flags_router)
app.include_router(chat_router)

@app.post("/api/seed", tags=["Seed Data"])
def trigger_seed_reports():
    msg = seed_flagship_annual_reports()
    return {"status": "success", "message": msg}

@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "Financial Research Workspace API",
        "milestones_active": [
            "Document Agent (PyMuPDF, sentence-transformers, FAISS vector index)",
            "Extraction Agent (Grounded structured metrics with page & chunk provenance)",
            "Red Flag Agent (Risk patterns & auditor qualification scan)",
            "Research Agent (Multi-part question decomposition & cited findings)",
            "Comparison Agent (Side-by-side corporate metric comparison)",
            "Report Agent (Executive summary & key financials report)",
            "Multi-Agent Orchestrator (Automated sequential pipeline execution)"
        ],
        "orchestration_framework": "LangGraph (StateGraph)",
        "llm_framework": "LangChain (ChatOpenAI / gpt-4o-mini with Grounded Synthesis)",
        "database_connected": DB_PATH.exists(),
        "database_path": str(DB_PATH)
    }

# If frontend dist exists, mount static files
FRONTEND_DIST = CURRENT_DIR.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
