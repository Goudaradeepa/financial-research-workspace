import os
import sys
import json
from pathlib import Path
import pytest
import pymupdf
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from document_agent import (
    extract_pdf_pages_pymupdf,
    chunk_pages_with_provenance,
    generate_embeddings_and_faiss_index,
    run_document_agent_pipeline
)
from extraction_agent import (
    extract_all_financial_metrics,
    search_faiss_chunks,
    TARGET_METRICS
)
from database import get_db_connection

client = TestClient(app)

@pytest.fixture(scope="module")
def sample_pdf_path(tmp_path_factory):
    """Creates a realistic 3-page financial sample PDF using PyMuPDF for testing."""
    tmp_dir = tmp_path_factory.mktemp("pdf_test")
    pdf_path = tmp_dir / "sample_financial_report.pdf"

    doc = pymupdf.open()
    
    # Page 1: Cover / Executive Summary
    p1 = doc.new_page()
    p1.insert_text(
        pymupdf.Point(50, 70),
        "ACME CORP ANNUAL FINANCIAL REPORT 2024\n"
        "Executive Summary and Business Overview\n\n"
        "ACME Corp operates globally across multiple technology segments.\n"
        "This report outlines our audited financial performance for Fiscal Year 2024.",
        fontsize=12
    )

    # Page 2: Income Statement
    p2 = doc.new_page()
    p2.insert_text(
        pymupdf.Point(50, 70),
        "CONSOLIDATED STATEMENTS OF OPERATIONS\n"
        "Fiscal Year Ended December 31, 2024 (in billions of USD, except per share data)\n\n"
        "Total Revenue was $45.2 billion for FY2024, representing revenue growth of 14.5%.\n"
        "Cost of Goods Sold: $21.1 billion.\n"
        "Gross Profit: $24.1 billion.\n"
        "Gross Margin was 53.3%.\n"
        "Operating Income: Operating profit was $12.4 billion.\n"
        "Operating Margin was 27.4%.\n"
        "EBITDA was $15.8 billion for the full year.\n"
        "Net Income: Net profit was $9.85 billion.\n"
        "Net Profit Margin was 21.8%.\n"
        "Diluted Earnings Per Share: diluted EPS was $4.62.",
        fontsize=11
    )

    # Page 3: Balance Sheet & Cash Flow
    p3 = doc.new_page()
    p3.insert_text(
        pymupdf.Point(50, 70),
        "CONSOLIDATED BALANCE SHEETS AND CASH FLOWS\n"
        "As of December 31, 2024 (in billions of USD)\n\n"
        "Total Assets were $88.6 billion as of year-end.\n"
        "Total Liabilities were $38.2 billion.\n"
        "Total Debt was $16.5 billion.\n"
        "Operating Cash Flow: $13.2 billion.\n"
        "Capital Expenditures: $3.1 billion.\n"
        "Free Cash Flow was $10.1 billion for FY2024.",
        fontsize=11
    )

    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


def test_pymupdf_extraction_and_page_preservation(sample_pdf_path):
    """Verifies PyMuPDF page-by-page extraction preserves page counts and text fidelity."""
    pages = extract_pdf_pages_pymupdf(Path(sample_pdf_path))
    assert len(pages) == 3
    assert pages[0]["page_number"] == 1
    assert "ACME CORP" in pages[0]["text"]
    assert pages[1]["page_number"] == 2
    assert "Operating profit" in pages[1]["text"]
    assert pages[2]["page_number"] == 3
    assert "Free Cash Flow" in pages[2]["text"]


def test_document_agent_pipeline_execution(sample_pdf_path):
    """Verifies end-to-end Document Agent pipeline: parsing, chunking, embedding, FAISS indexing."""
    # Create test session in DB
    session_res = client.post("/api/sessions", json={
        "name": "Pipeline Verification Session",
        "description": "Session for testing Document & Extraction agents"
    })
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    # Insert document record (clean up if left from previous run)
    doc_id = "test-doc-agent-001"
    with get_db_connection() as conn:
        conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (doc_id,))
        conn.execute("DELETE FROM financial_documents WHERE id = ?", (doc_id,))
        now = "2026-09-16T10:00:00Z"
        conn.execute("""
            INSERT INTO financial_documents (
                id, session_id, company_name, document_name, document_type,
                file_path, file_size_bytes, upload_date, processing_status, page_count,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id, session_id, "ACME Corp", "sample_financial_report.pdf", "10-K",
            sample_pdf_path, os.path.getsize(sample_pdf_path), now, "PENDING", 3,
            now, now
        ))
        conn.commit()

    # Run Document Agent pipeline
    pipeline_res = run_document_agent_pipeline(doc_id)
    assert pipeline_res["status"] == "READY"
    assert pipeline_res["page_count"] == 3
    assert pipeline_res["chunk_count"] > 0
    assert os.path.exists(pipeline_res["index_path"])

    # Verify vector search over the FAISS index
    search_hits = search_faiss_chunks(doc_id, "operating profit and EBITDA", top_k=3)
    assert len(search_hits) > 0
    # Page 2 contains operating profit and EBITDA
    hit_pages = [h["page_number"] for h in search_hits]
    assert 2 in hit_pages
    assert search_hits[0]["similarity_score"] > 0.0


def test_extraction_agent_grounded_metrics(sample_pdf_path):
    """Verifies Extraction Agent extracts grounded metrics with exact page provenance and no hallucinations."""
    doc_id = "test-doc-agent-001"

    metrics = extract_all_financial_metrics(doc_id)
    assert len(metrics) == len(TARGET_METRICS)

    # Convert to dictionary keyed by metric_key for robust assertions
    metric_dict = {m["metric_key"]: m for m in metrics}

    # 1. Total Revenue
    assert "revenue" in metric_dict
    rev = metric_dict["revenue"]
    assert rev["value"] == 45.2
    assert rev["unit"] == "$B"
    assert rev["source_page"] == 2
    assert rev["source_chunk_id"] is not None

    # 2. Operating Profit
    op = metric_dict["operating_profit"]
    assert op["value"] == 12.4
    assert op["source_page"] == 2

    # 3. EBITDA
    ebitda = metric_dict["ebitda"]
    assert ebitda["value"] == 15.8
    assert ebitda["source_page"] == 2

    # 4. Total Assets & Free Cash Flow
    assets = metric_dict["total_assets"]
    assert assets["value"] == 88.6
    assert assets["source_page"] == 3

    fcf = metric_dict["free_cash_flow"]
    assert fcf["value"] == 10.1
    assert fcf["source_page"] == 3

    # Verify stored in DB
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT financial_metrics, session_id FROM financial_documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        assert row is not None
        stored_metrics = json.loads(row[0])
        assert len(stored_metrics) == len(TARGET_METRICS)
        test_session_id = row[1]
        
    # Clean up test session and doc to prevent cluttering user workspace
    if test_session_id:
        client.delete(f"/api/sessions/{test_session_id}")


def test_seed_flagship_reports_available_and_indexed():
    """Verifies seed flagship reports (Apple, Microsoft, Tesla, NVIDIA) are indexed in FAISS."""
    res = client.get("/api/sessions/seed-session-flagship-reports/documents")
    assert res.status_code == 200
    docs = res.json()
    assert len(docs) >= 4

    companies = {d["company_name"] for d in docs}
    assert any("Apple" in c for c in companies)
    assert any("Microsoft" in c for c in companies)
    assert any("Tesla" in c for c in companies)
    assert any("NVIDIA" in c for c in companies)

    # Check status and chunk counts
    for doc in docs:
        assert doc["processing_status"] in ("READY", "COMPLETED")
        assert doc["page_count"] >= 3

        detail_res = client.get(f"/api/sessions/seed-session-flagship-reports/documents/{doc['id']}")
        assert detail_res.status_code == 200
        assert len(detail_res.json()["chunks"]) > 0

        # Check metrics endpoint for each document
        metrics_res = client.get(f"/api/sessions/seed-session-flagship-reports/documents/{doc['id']}/metrics")
        assert metrics_res.status_code == 200
        metrics = metrics_res.json()
        assert len(metrics) > 0
        # Ensure at least Revenue is extracted
        rev = next((m for m in metrics if m["metric_key"] == "revenue"), None)
        assert rev is not None
        assert rev["value"] is not None
        assert rev["source_page"] is not None
