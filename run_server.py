import sys
from pathlib import Path
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "backend"))

if __name__ == "__main__":
    print("=" * 68)
    print("  FINANCIAL RESEARCH WORKSPACE - MULTI-AGENT SYSTEM HUB")
    print("  Active Agents:")
    print("    1. Document Agent       (PDF Parsing, Chunking & FAISS Indexing)")
    print("    2. Extraction Agent     (Grounded Structured Metric Extraction)")
    print("    3. Red Flag Agent       (7 Risk Rules & Auditor Qualification Scan)")
    print("    4. Orchestrator Agent   (Sequential Pipeline & Audit Logging)")
    print("    5. Research Agent       (Decomposition & Cited Semantic Search)")
    print("    6. Comparison Agent     (Side-by-Side Multi-Company Matrix)")
    print("    7. Report Agent         (Executive Summary & Key Financials)")
    print("  Unified Web Workspace: http://127.0.0.1:8000")
    print("  FastAPI Swagger Docs:  http://127.0.0.1:8000/docs")
    print("=" * 68)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
