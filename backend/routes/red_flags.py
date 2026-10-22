from typing import List
from fastapi import APIRouter, HTTPException, status

from database import get_db_connection
from models import RedFlagItem, AgentRunItem
from red_flag_agent import analyze_red_flags, get_document_red_flags, get_session_red_flags
from orchestrator import get_document_agent_runs, get_session_agent_runs

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["Red Flag Agent"])

@router.get("/red-flags", response_model=List[RedFlagItem])
def list_session_red_flags(session_id: str):
    """Retrieves all detected red flags across all documents in a research session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM research_sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Research session not found")
    conn.close()

    return get_session_red_flags(session_id)

@router.get("/documents/{document_id}/red-flags", response_model=List[RedFlagItem])
def list_document_red_flags(session_id: str, document_id: str):
    """Retrieves all red flag findings and pattern checks for a specific document."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM financial_documents WHERE id = ? AND session_id = ?", (document_id, session_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")
    conn.close()

    return get_document_red_flags(document_id)

@router.post("/documents/{document_id}/red-flags/analyze", response_model=List[RedFlagItem])
def trigger_red_flag_analysis(session_id: str, document_id: str):
    """Triggers on-demand red flag analysis on an indexed document."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM financial_documents WHERE id = ? AND session_id = ?", (document_id, session_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")
    conn.close()

    try:
        flags = analyze_red_flags(document_id)
        return flags
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Red flag analysis failed: {str(e)}")

@router.get("/documents/{document_id}/agent-runs", response_model=List[AgentRunItem])
def list_document_agent_runs(session_id: str, document_id: str):
    """Retrieves the multi-agent orchestrator audit trail for a document."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM financial_documents WHERE id = ? AND session_id = ?", (document_id, session_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")
    conn.close()

    return get_document_agent_runs(document_id)

@router.get("/agent-runs", response_model=List[AgentRunItem])
def list_session_agent_runs(session_id: str):
    """Retrieves the multi-agent orchestrator audit trail across all documents in a session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM research_sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Research session not found")
    conn.close()

    return get_session_agent_runs(session_id)
