import os
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from fastapi.responses import FileResponse

from database import get_db_connection, STORAGE_DIR
from models import (
    FinancialDocumentResponse, 
    FinancialDocumentDetailResponse, 
    FinancialDocumentUpdate,
    DocumentChunk, 
    ExtractedMetricItem,
    ProcessingStatus
)
from document_agent import run_document_agent_pipeline
from extraction_agent import extract_all_financial_metrics
from company_detector import detect_company_name
from orchestrator import run_full_document_pipeline

router = APIRouter(prefix="/api/sessions/{session_id}/documents", tags=["Financial Documents"])

def background_doc_ingest(doc_id: str):
    """Executes full multi-agent pipeline: Document Agent -> Extraction Agent -> Red Flag Agent."""
    try:
        run_full_document_pipeline(doc_id)
    except Exception as e:
        print(f"Error in background_doc_ingest for {doc_id}: {e}")

@router.post("", response_model=List[FinancialDocumentResponse], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    session_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    company_name: Optional[str] = Form(None),
    company_names: Optional[str] = Form(None)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, ticker FROM research_sessions WHERE id = ?", (session_id,))
    session = cursor.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Research session not found")

    session_folder = STORAGE_DIR / "sessions" / session_id
    session_folder.mkdir(parents=True, exist_ok=True)

    created_docs = []
    now = datetime.utcnow().isoformat()

    for uploaded in files:
        raw_filename = uploaded.filename or "document"
        safe_filename = Path(raw_filename).name
        ext = Path(safe_filename).suffix.lower() or ".bin"
        doc_id = str(uuid.uuid4())

        stored_name = f"{doc_id}_{safe_filename}"
        target_path = session_folder / stored_name

        content = await uploaded.read()
        file_size = len(content)
        with open(target_path, "wb") as f:
            f.write(content)

        # Strictly independent company identification:
        # 1. User-provided company name for this file (if given)
        # 2. Detected from filename or PDF cover/text
        # 3. NEVER defaulted to session["name"] or session["ticker"]
        custom_company = None
        if company_names:
            try:
                mapping = json.loads(company_names)
                if isinstance(mapping, dict):
                    custom_company = mapping.get(safe_filename) or mapping.get(raw_filename)
            except Exception:
                pass
        if not custom_company and company_name and company_name.strip():
            custom_company = company_name.strip()

        doc_company = detect_company_name(safe_filename, target_path, user_hint=custom_company)

        cursor.execute("""
        INSERT INTO financial_documents (
            id, session_id, company_name, document_name, document_type, file_path,
            upload_date, processing_status, file_size_bytes, page_count, word_count,
            summary_snippet, extracted_text, financial_metrics, error_message, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, NULL, NULL, NULL, NULL, ?, ?)
        """, (
            doc_id,
            session_id,
            doc_company,
            safe_filename,
            "Detecting...",
            str(target_path),
            now,
            ProcessingStatus.PENDING.value,
            file_size,
            now,
            now
        ))

        created_docs.append(FinancialDocumentResponse(
            id=doc_id,
            session_id=session_id,
            company_name=doc_company,
            document_name=safe_filename,
            document_type="Detecting...",
            file_path=str(target_path),
            upload_date=now,
            processing_status=ProcessingStatus.PENDING,
            file_size_bytes=file_size,
            page_count=0,
            word_count=0,
            summary_snippet=None,
            error_message=None,
            created_at=now,
            updated_at=now
        ))

        # Run Document Agent & Extraction Agent in background
        background_tasks.add_task(background_doc_ingest, doc_id)

    conn.commit()
    conn.close()

    return created_docs

@router.get("", response_model=List[FinancialDocumentResponse])
def list_documents(session_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM research_sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Research session not found")

    cursor.execute("""
    SELECT id, session_id, company_name, document_name, document_type, file_path, 
           upload_date, processing_status, file_size_bytes, page_count, word_count, 
           summary_snippet, error_message, created_at, updated_at,
           relevance_status, relevance_reason
    FROM financial_documents
    WHERE session_id = ?
    ORDER BY upload_date DESC
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append(FinancialDocumentResponse(
            id=r["id"],
            session_id=r["session_id"],
            company_name=r["company_name"],
            document_name=r["document_name"],
            document_type=r["document_type"],
            file_path=r["file_path"],
            upload_date=r["upload_date"],
            processing_status=ProcessingStatus(r["processing_status"]),
            file_size_bytes=r["file_size_bytes"] or 0,
            page_count=r["page_count"] or 0,
            word_count=r["word_count"] or 0,
            summary_snippet=r["summary_snippet"],
            relevance_status=r["relevance_status"] if "relevance_status" in r.keys() and r["relevance_status"] else "FINANCIAL",
            relevance_reason=r["relevance_reason"] if "relevance_reason" in r.keys() else None,
            error_message=r["error_message"],
            created_at=r["created_at"],
            updated_at=r["updated_at"]
        ))
    return result

@router.get("/{document_id}", response_model=FinancialDocumentDetailResponse)
def get_document(session_id: str, document_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM financial_documents WHERE id = ? AND session_id = ?
    """, (document_id, session_id))
    doc = cursor.fetchone()

    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Financial document not found")

    cursor.execute("""
    SELECT id, chunk_index, content, token_estimate, metadata
    FROM document_chunks
    WHERE document_id = ?
    ORDER BY chunk_index ASC
    """, (document_id,))
    chunk_rows = cursor.fetchall()
    conn.close()

    chunks = []
    for c in chunk_rows:
        meta = json.loads(c["metadata"]) if c["metadata"] else {}
        chunks.append(DocumentChunk(
            id=c["id"],
            chunk_index=c["chunk_index"],
            content=c["content"],
            token_estimate=c["token_estimate"] or 0,
            metadata=meta
        ))

    # Parse financial metrics / structured metrics
    structured_metrics: List[ExtractedMetricItem] = []
    financial_metrics = None
    if doc["financial_metrics"]:
        try:
            parsed = json.loads(doc["financial_metrics"])
            financial_metrics = parsed
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "metric_name" in item:
                        structured_metrics.append(ExtractedMetricItem(
                            metric_name=item["metric_name"],
                            metric_key=item.get("metric_key", item["metric_name"]),
                            value=item.get("value"),
                            unit=item.get("unit"),
                            financial_year=item.get("financial_year"),
                            source_page=item.get("source_page"),
                            source_chunk_id=item.get("source_chunk_id"),
                            status=item.get("status", "available"),
                            confidence=item.get("confidence", "high")
                        ))
        except Exception:
            financial_metrics = doc["financial_metrics"]

    return FinancialDocumentDetailResponse(
        id=doc["id"],
        session_id=doc["session_id"],
        company_name=doc["company_name"],
        document_name=doc["document_name"],
        document_type=doc["document_type"],
        relevance_status=doc["relevance_status"] if "relevance_status" in doc.keys() and doc["relevance_status"] else "FINANCIAL",
        relevance_reason=doc["relevance_reason"] if "relevance_reason" in doc.keys() else None,
        file_path=doc["file_path"],
        upload_date=doc["upload_date"],
        processing_status=ProcessingStatus(doc["processing_status"]),
        file_size_bytes=doc["file_size_bytes"] or 0,
        page_count=doc["page_count"] or 0,
        word_count=doc["word_count"] or 0,
        summary_snippet=doc["summary_snippet"],
        extracted_text=doc["extracted_text"],
        financial_metrics=financial_metrics,
        structured_metrics=structured_metrics,
        chunks=chunks,
        error_message=doc["error_message"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"]
    )

@router.get("/{document_id}/metrics", response_model=List[ExtractedMetricItem])
def get_extracted_metrics(session_id: str, document_id: str):
    """
    Extraction Agent Endpoint (Milestone 2): Returns structured financial metrics 
    retrieved from the FAISS vector index with source page and chunk provenance.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT financial_metrics, relevance_status FROM financial_documents WHERE id = ? AND session_id = ?
    """, (document_id, session_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    if row["relevance_status"] == "NON_FINANCIAL":
        return []

    if not row["financial_metrics"]:
        # Run Extraction Agent on demand
        return extract_all_financial_metrics(document_id)

    try:
        metrics_list = json.loads(row["financial_metrics"])
        if isinstance(metrics_list, list):
            return metrics_list
    except Exception:
        pass

    return extract_all_financial_metrics(document_id)

@router.post("/{document_id}/extract-metrics", response_model=List[ExtractedMetricItem])
def trigger_extraction_agent(session_id: str, document_id: str):
    """
    Triggers Extraction Agent (Milestone 2) to search FAISS and extract structured metrics.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT relevance_status FROM financial_documents WHERE id = ? AND session_id = ?", (document_id, session_id))
    row = cursor.fetchone()
    conn.close()

    if row and row["relevance_status"] == "NON_FINANCIAL":
        return []

    return extract_all_financial_metrics(document_id)

@router.get("/{document_id}/download")
def download_document(session_id: str, document_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT document_name, file_path FROM financial_documents WHERE id = ? AND session_id = ?
    """, (document_id, session_id))
    doc = cursor.fetchone()
    conn.close()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    path = Path(doc["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File content missing on storage")

    return FileResponse(
        path=str(path),
        filename=doc["document_name"],
        media_type="application/octet-stream"
    )

@router.patch("/{document_id}", response_model=FinancialDocumentResponse)
def update_document_metadata(session_id: str, document_id: str, payload: FinancialDocumentUpdate):
    """Updates document metadata, including company_name, independently from session."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM financial_documents WHERE id = ? AND session_id = ?", (document_id, session_id))
    doc = cursor.fetchone()
    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")

    new_company = payload.company_name.strip() if payload.company_name is not None else doc["company_name"]
    new_doc_name = payload.document_name.strip() if payload.document_name is not None else doc["document_name"]
    new_doc_type = payload.document_type.strip() if payload.document_type is not None else doc["document_type"]
    now = datetime.utcnow().isoformat()

    cursor.execute("""
    UPDATE financial_documents
    SET company_name = ?, document_name = ?, document_type = ?, updated_at = ?
    WHERE id = ? AND session_id = ?
    """, (new_company, new_doc_name, new_doc_type, now, document_id, session_id))
    conn.commit()

    cursor.execute("SELECT * FROM financial_documents WHERE id = ? AND session_id = ?", (document_id, session_id))
    updated = cursor.fetchone()
    conn.close()

    return FinancialDocumentResponse(
        id=updated["id"],
        session_id=updated["session_id"],
        company_name=updated["company_name"],
        document_name=updated["document_name"],
        document_type=updated["document_type"],
        file_path=updated["file_path"],
        upload_date=updated["upload_date"],
        processing_status=ProcessingStatus(updated["processing_status"]),
        file_size_bytes=updated["file_size_bytes"] or 0,
        page_count=updated["page_count"] or 0,
        word_count=updated["word_count"] or 0,
        summary_snippet=updated["summary_snippet"],
        error_message=updated["error_message"],
        created_at=updated["created_at"],
        updated_at=updated["updated_at"]
    )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(session_id: str, document_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT file_path FROM financial_documents WHERE id = ? AND session_id = ?
    """, (document_id, session_id))
    doc = cursor.fetchone()

    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(doc["file_path"])

    cursor.execute("DELETE FROM financial_documents WHERE id = ?", (document_id,))
    conn.commit()
    conn.close()

    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            print(f"Warning: Could not delete physical file {file_path}: {e}")

    # Remove FAISS index and metadata
    index_path = STORAGE_DIR / "vector_indices" / f"{document_id}.faiss"
    meta_path = STORAGE_DIR / "vector_indices" / f"{document_id}_meta.json"
    if index_path.exists():
        index_path.unlink(missing_ok=True)
    if meta_path.exists():
        meta_path.unlink(missing_ok=True)

    return None

@router.post("/{document_id}/reprocess", response_model=FinancialDocumentResponse)
def reprocess_doc(session_id: str, document_id: str, background_tasks: BackgroundTasks):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM financial_documents WHERE id = ? AND session_id = ?", (document_id, session_id))
    doc = cursor.fetchone()
    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")

    now = datetime.utcnow().isoformat()
    cursor.execute("""
    UPDATE financial_documents 
    SET processing_status = 'PENDING', error_message = NULL, updated_at = ? 
    WHERE id = ?
    """, (now, document_id))
    conn.commit()
    conn.close()

    background_tasks.add_task(background_doc_ingest, document_id)

    return FinancialDocumentResponse(
        id=doc["id"],
        session_id=doc["session_id"],
        company_name=doc["company_name"],
        document_name=doc["document_name"],
        document_type=doc["document_type"],
        file_path=doc["file_path"],
        upload_date=doc["upload_date"],
        processing_status=ProcessingStatus.PENDING,
        file_size_bytes=doc["file_size_bytes"] or 0,
        page_count=doc["page_count"] or 0,
        word_count=doc["word_count"] or 0,
        summary_snippet=doc["summary_snippet"],
        error_message=None,
        created_at=doc["created_at"],
        updated_at=now
    )
