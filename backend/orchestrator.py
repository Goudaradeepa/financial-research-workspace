import uuid
import json
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

from database import get_db_connection
from document_agent import run_document_agent_pipeline
from extraction_agent import extract_all_financial_metrics
from red_flag_agent import analyze_red_flags

def record_agent_run(
    session_id: str,
    document_id: str,
    agent_name: str,
    status: str,
    started_at: str,
    completed_at: Optional[str] = None,
    output_summary: Optional[str] = None,
    error_message: Optional[str] = None
) -> str:
    """Records an agent run event in the agent_runs audit trail table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    run_id = str(uuid.uuid4())

    cursor.execute("""
    INSERT INTO agent_runs (
        id, session_id, document_id, agent_name, status,
        started_at, completed_at, output_summary, error_message
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        session_id,
        document_id,
        agent_name,
        status,
        started_at,
        completed_at,
        output_summary,
        error_message
    ))
    conn.commit()
    conn.close()
    return run_id

def update_agent_run(
    run_id: str,
    status: str,
    completed_at: str,
    output_summary: Optional[str] = None,
    error_message: Optional[str] = None
):
    """Updates an existing agent run record upon completion or failure."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE agent_runs
    SET status = ?, completed_at = ?, output_summary = ?, error_message = ?
    WHERE id = ?
    """, (status, completed_at, output_summary, error_message, run_id))
    conn.commit()
    conn.close()

def run_full_document_pipeline(document_id: str) -> Dict[str, Any]:
    """
    Coordinates multi-agent execution sequentially:
    1. Document Agent -> Parse PDF, chunk with provenance, embed, index in FAISS
    2. Extraction Agent -> Vector retrieval of grounded financial metrics
    3. Red Flag Agent -> Risk pattern analysis and auditor qualification scan
    4. Final Document Analysis -> Mark document status as COMPLETED
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT session_id, document_name FROM financial_documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()
    conn.close()

    if not doc:
        raise ValueError(f"Document {document_id} not found in database")

    session_id = doc["session_id"]
    doc_name = doc["document_name"]

    print(f"[Orchestrator] Starting multi-agent pipeline for document '{doc_name}' ({document_id})...")

    # -------------------------------------------------------------
    # Step 1: Document Agent
    # -------------------------------------------------------------
    doc_start = datetime.utcnow().isoformat()
    doc_run_id = record_agent_run(
        session_id=session_id,
        document_id=document_id,
        agent_name="Document Agent",
        status="PROCESSING",
        started_at=doc_start
    )

    try:
        doc_result = run_document_agent_pipeline(document_id)
        doc_end = datetime.utcnow().isoformat()
        update_agent_run(
            run_id=doc_run_id,
            status="COMPLETED",
            completed_at=doc_end,
            output_summary=f"Indexed {doc_result.get('page_count', 0)} pages, {doc_result.get('chunk_count', 0)} chunks, {doc_result.get('vector_count', 0)} vectors into FAISS."
        )
    except Exception as e:
        err_msg = str(e)
        doc_end = datetime.utcnow().isoformat()
        update_agent_run(
            run_id=doc_run_id,
            status="FAILED",
            completed_at=doc_end,
            error_message=err_msg
        )
        print(f"[Orchestrator] Document Agent failed for {document_id}: {err_msg}. Aborting pipeline.")
        return {"document_id": document_id, "status": "FAILED", "failed_at": "Document Agent", "error": err_msg}

    # -------------------------------------------------------------
    # Step 1.5: Document Relevance Validation Gate
    # -------------------------------------------------------------
    relevance_status = doc_result.get("relevance_status", "FINANCIAL")
    relevance_reason = doc_result.get("relevance_reason")

    val_start = datetime.utcnow().isoformat()
    val_run_id = record_agent_run(
        session_id=session_id,
        document_id=document_id,
        agent_name="Document Relevance Validation",
        status="PROCESSING",
        started_at=val_start
    )
    val_end = datetime.utcnow().isoformat()
    update_agent_run(
        run_id=val_run_id,
        status="COMPLETED",
        completed_at=val_end,
        output_summary=f"Classification: {relevance_status}. Reason: {relevance_reason}"
    )

    if relevance_status == "NON_FINANCIAL":
        print(f"[Orchestrator] Document {document_id} classified as NON_FINANCIAL. Skipping financial analysis.")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE financial_documents
        SET processing_status = 'COMPLETED', financial_metrics = '[]', updated_at = ?
        WHERE id = ?
        """, (val_end, document_id))
        conn.commit()
        conn.close()

        return {
            "document_id": document_id,
            "status": "Unsupported Document",
            "classification": "NON_FINANCIAL",
            "reason": "This PDF does not appear to be a financial document. Financial analysis was skipped.",
            "relevance_reason": relevance_reason,
            "document_agent": "COMPLETED",
            "extraction_agent": "SKIPPED",
            "red_flag_agent": "SKIPPED"
        }

    if relevance_status == "UNCERTAIN":
        print(f"[Orchestrator] Document {document_id} classified as UNCERTAIN. Financial analysis not started.")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE financial_documents
        SET processing_status = 'READY', financial_metrics = '[]', updated_at = ?
        WHERE id = ?
        """, (val_end, document_id))
        conn.commit()
        conn.close()

        return {
            "document_id": document_id,
            "status": "Document Type Uncertain",
            "classification": "UNCERTAIN",
            "reason": relevance_reason or "Unable to confidently determine whether this document is a financial report.",
            "relevance_reason": relevance_reason,
            "document_agent": "COMPLETED",
            "extraction_agent": "NOT_STARTED",
            "red_flag_agent": "NOT_STARTED"
        }

    # -------------------------------------------------------------
    # Step 2: Extraction Agent
    # -------------------------------------------------------------
    ext_start = datetime.utcnow().isoformat()
    ext_run_id = record_agent_run(
        session_id=session_id,
        document_id=document_id,
        agent_name="Extraction Agent",
        status="PROCESSING",
        started_at=ext_start
    )

    try:
        extracted_metrics = extract_all_financial_metrics(document_id)
        ext_end = datetime.utcnow().isoformat()
        available_count = sum(1 for m in extracted_metrics if m.get("status") == "available")
        update_agent_run(
            run_id=ext_run_id,
            status="COMPLETED",
            completed_at=ext_end,
            output_summary=f"Extracted {available_count} available grounded metrics ({len(extracted_metrics)} target indicators)."
        )
    except Exception as e:
        err_msg = str(e)
        ext_end = datetime.utcnow().isoformat()
        update_agent_run(
            run_id=ext_run_id,
            status="FAILED",
            completed_at=ext_end,
            error_message=err_msg
        )
        print(f"[Orchestrator] Extraction Agent failed for {document_id}: {err_msg}. Aborting pipeline.")
        return {"document_id": document_id, "status": "FAILED", "failed_at": "Extraction Agent", "error": err_msg}

    # -------------------------------------------------------------
    # Step 3: Red Flag Agent
    # -------------------------------------------------------------
    flag_start = datetime.utcnow().isoformat()
    flag_run_id = record_agent_run(
        session_id=session_id,
        document_id=document_id,
        agent_name="Red Flag Agent",
        status="PROCESSING",
        started_at=flag_start
    )

    try:
        flags = analyze_red_flags(document_id)
        flag_end = datetime.utcnow().isoformat()
        active_flags_count = sum(1 for f in flags if f.get("status") == "FLAGGED")
        update_agent_run(
            run_id=flag_run_id,
            status="COMPLETED",
            completed_at=flag_end,
            output_summary=f"Analyzed 7 risk indicators: {active_flags_count} flagged risks, {len(flags) - active_flags_count} clean or insufficient evidence."
        )
    except Exception as e:
        err_msg = str(e)
        flag_end = datetime.utcnow().isoformat()
        update_agent_run(
            run_id=flag_run_id,
            status="FAILED",
            completed_at=flag_end,
            error_message=err_msg
        )
        print(f"[Orchestrator] Red Flag Agent failed for {document_id}: {err_msg}")
        return {"document_id": document_id, "status": "FAILED", "failed_at": "Red Flag Agent", "error": err_msg}

    # -------------------------------------------------------------
    # Step 4: Finalize Document Analysis Status
    # -------------------------------------------------------------
    conn = get_db_connection()
    cursor = conn.cursor()
    final_now = datetime.utcnow().isoformat()
    cursor.execute("""
    UPDATE financial_documents
    SET processing_status = 'COMPLETED', updated_at = ?
    WHERE id = ?
    """, (final_now, document_id))
    conn.commit()
    conn.close()

    print(f"[Orchestrator] Multi-agent orchestration completed successfully for {document_id}.")
    return {
        "document_id": document_id,
        "status": "COMPLETED",
        "document_agent": "COMPLETED",
        "extraction_agent": "COMPLETED",
        "red_flag_agent": "COMPLETED",
        "flags_detected": active_flags_count
    }

def get_document_agent_runs(document_id: str) -> List[Dict[str, Any]]:
    """Fetches the orchestration audit trail for a specific document."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, session_id, document_id, agent_name, status,
           started_at, completed_at, output_summary, error_message
    FROM agent_runs
    WHERE document_id = ?
    ORDER BY started_at ASC
    """, (document_id,))
    rows = cursor.fetchall()
    conn.close()

    runs = []
    for r in rows:
        runs.append({
            "id": r["id"],
            "session_id": r["session_id"],
            "document_id": r["document_id"],
            "agent_name": r["agent_name"],
            "status": r["status"],
            "started_at": r["started_at"],
            "completed_at": r["completed_at"],
            "output_summary": r["output_summary"],
            "error_message": r["error_message"]
        })
    return runs

def get_session_agent_runs(session_id: str) -> List[Dict[str, Any]]:
    """Fetches the orchestration audit trail for all documents in a session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, session_id, document_id, agent_name, status,
           started_at, completed_at, output_summary, error_message
    FROM agent_runs
    WHERE session_id = ?
    ORDER BY started_at DESC
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()

    runs = []
    for r in rows:
        runs.append({
            "id": r["id"],
            "session_id": r["session_id"],
            "document_id": r["document_id"],
            "agent_name": r["agent_name"],
            "status": r["status"],
            "started_at": r["started_at"],
            "completed_at": r["completed_at"],
            "output_summary": r["output_summary"],
            "error_message": r["error_message"]
        })
    return runs
