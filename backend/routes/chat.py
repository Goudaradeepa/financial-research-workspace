import os
import re
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from database import get_db_connection
from models import ResearchCitation, ComparisonRequest, ComparisonResponse, GeneratedReportResponse
from research_agent import answer_financial_research_query
from comparison_agent import compare_company_documents
from red_flag_agent import get_session_red_flags
from report_agent import generate_document_report, get_document_report

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["Conversational Research & Multi-Agent"])

class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User financial inquiry")
    document_id: Optional[str] = Field(None, description="Optional document context")

class ChatMessageResponse(BaseModel):
    message: str
    intent: str  # research, comparison, red_flags, clarification
    answer: str
    sources: List[ResearchCitation] = []
    agent_used: str
    suggested_queries: Optional[List[str]] = None

from langgraph_orchestrator import run_langgraph_research

@router.post("/chat", response_model=ChatMessageResponse)
def handle_chat_message(session_id: str, payload: ChatMessageRequest):
    """
    Intelligent Conversational Research Desk powered by LangGraph StateGraph:
    Classifies intent and coordinates Research Agent, Comparison Agent, Red Flag Agent,
    and LangChain LLM synthesis node.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM research_sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Research session not found")
    conn.close()

    raw_query = payload.message.strip()
    
    # Execute full LangGraph StateGraph
    graph_res = run_langgraph_research(
        session_id=session_id,
        query=raw_query,
        document_id=payload.document_id
    )

    sources = [
        ResearchCitation(
            company_name=s.get("company_name"),
            document_name=s.get("document_name"),
            source_page=s.get("source_page"),
            source_chunk_id=s.get("source_chunk_id"),
            snippet=s.get("snippet")
        )
        for s in graph_res.get("sources", [])
    ]

    return ChatMessageResponse(
        message=raw_query,
        intent=graph_res.get("intent", "research"),
        answer=graph_res.get("answer", ""),
        sources=sources,
        agent_used=graph_res.get("agent_used", "LangGraph Multi-Agent System"),
        suggested_queries=graph_res.get("suggested_queries")
    )

@router.get("/graph/info", tags=["LangGraph & LangChain"])
def get_graph_architecture():
    """Returns the LangGraph StateGraph topology, nodes, and LLM configuration."""
    return {
        "framework": "LangGraph",
        "llm_framework": "LangChain",
        "graph_nodes": [
            "supervisor_router",
            "research_agent",
            "red_flag_agent",
            "comparison_agent",
            "llm_synthesis"
        ],
        "state_schema": [
            "session_id", "query", "document_id", "intent",
            "sub_topics", "retrieved_chunks", "verified_metrics",
            "findings", "sources", "final_answer", "agent_used"
        ],
        "active_llm": os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini"),
        "fallback_enabled": True
    }

@router.get("/chat/history")
def get_chat_history(session_id: str):
    """Retrieves conversation history for the session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, session_id, query_text, answer_text, agent_used, sources, created_at
    FROM research_queries
    WHERE session_id = ?
    ORDER BY created_at ASC
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        history.append({
            "id": r["id"],
            "query": r["query_text"],
            "answer": r["answer_text"],
            "agent_used": r["agent_used"],
            "sources": json.loads(r["sources"]) if r["sources"] else [],
            "created_at": r["created_at"]
        })
    return history

@router.post("/compare", response_model=ComparisonResponse)
def trigger_comparison(session_id: str, payload: ComparisonRequest):
    """Executes the Comparison Agent for selected documents or all session documents."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM research_sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Research session not found")
    conn.close()

    return compare_company_documents(session_id, payload.document_ids)

@router.post("/documents/{document_id}/report", response_model=GeneratedReportResponse)
def create_document_report(session_id: str, document_id: str):
    """Generates an executive summary and key financials report using the Report Agent."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM financial_documents WHERE id = ? AND session_id = ?", (document_id, session_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")
    conn.close()

    try:
        report = generate_document_report(document_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@router.get("/documents/{document_id}/report", response_model=Optional[GeneratedReportResponse])
def fetch_document_report(session_id: str, document_id: str):
    """Retrieves a previously generated report for a document."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM financial_documents WHERE id = ? AND session_id = ?", (document_id, session_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")
    conn.close()

    report = get_document_report(document_id)
    if not report:
        # Generate on-demand if not already cached
        report = generate_document_report(document_id)
    return report
