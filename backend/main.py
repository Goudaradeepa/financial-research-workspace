import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, DB_PATH
from routes.sessions import router as sessions_router
from routes.documents import router as documents_router

# Initialize database tables
init_db()

app = FastAPI(
    title="Financial Research Workspace API (Milestone 1)",
    description="Backend API for Document Processing Pipeline & FAISS Vector Indexing (PyMuPDF, Chunking, Sentence-Transformers, FAISS, SQLite)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router)
app.include_router(documents_router)

@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "Financial Research Workspace API - Milestone 1",
        "milestones_active": [
            "Document Agent (PyMuPDF, sentence-transformers, FAISS vector index)",
            "Research Sessions & Document Management (SQLite)"
        ],
        "database_connected": DB_PATH.exists(),
        "database_path": str(DB_PATH)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
