import os
import sys
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from processor import process_document
from database import get_db_connection

client = TestClient(app)

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True

def test_research_session_lifecycle():
    # 1. Create research session with ID, name, description, created_at, updated_at
    payload = {
        "name": "Apple Q3 2024 Deep Dive",
        "description": "Comprehensive review of Q3 results and services growth.",
        "ticker": "AAPL",
        "tags": ["Tech", "MegaCap", "Hardware", "Services"]
    }
    create_res = client.post("/api/sessions", json=payload)
    assert create_res.status_code == 201
    session_data = create_res.json()
    session_id = session_data["id"]
    assert session_data["name"] == payload["name"]
    assert session_data["description"] == payload["description"]
    assert "created_at" in session_data
    assert "updated_at" in session_data

    # 2. Get session
    get_res = client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == session_id

    # 3. Update session
    update_res = client.put(f"/api/sessions/{session_id}", json={
        "name": "Apple Q3 2024 - Updated Analysis",
        "description": "Updated research notes."
    })
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Apple Q3 2024 - Updated Analysis"

    # 4. List sessions
    list_res = client.get("/api/sessions")
    assert list_res.status_code == 200
    all_sessions = list_res.json()
    assert any(s["id"] == session_id for s in all_sessions)

    # 5. Delete session
    del_res = client.delete(f"/api/sessions/{session_id}")
    assert del_res.status_code == 204

    # 6. Verify 404 after deletion
    get_after_del = client.get(f"/api/sessions/{session_id}")
    assert get_after_del.status_code == 404

def test_financial_document_schema_and_processing():
    # Create test session
    session_res = client.post("/api/sessions", json={
        "name": "Multi-Doc Financial Test Session",
        "ticker": "MSFT",
        "description": "Testing multiple financial document uploads and classifications."
    })
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    # Upload files
    files_to_upload = [
        ("files", ("Apple_Q3_2024_Earnings_Call_Transcript.txt", open(SAMPLE_DIR / "Apple_Q3_2024_Earnings_Call_Transcript.txt", "rb"), "text/plain")),
        ("files", ("Microsoft_FY2024_Form_10K_Annual_Report.txt", open(SAMPLE_DIR / "Microsoft_FY2024_Form_10K_Annual_Report.txt", "rb"), "text/plain")),
        ("files", ("Tesla_Financial_Performance_and_Deliveries.csv", open(SAMPLE_DIR / "Tesla_Financial_Performance_and_Deliveries.csv", "rb"), "text/csv")),
        ("files", ("Sample_Blank_Form_10K.pdf", open(SAMPLE_DIR / "Sample_Blank_Form_10K.pdf", "rb"), "application/pdf"))
    ]

    upload_res = client.post(f"/api/sessions/{session_id}/documents", files=files_to_upload)
    assert upload_res.status_code == 201
    uploaded_docs = upload_res.json()
    assert len(uploaded_docs) == 4

    # Validate Schema Fields on uploaded documents
    for doc in uploaded_docs:
        assert "id" in doc
        assert doc["session_id"] == session_id
        assert doc["company_name"] is not None
        assert "document_name" in doc
        assert "document_type" in doc
        assert "file_path" in doc
        assert "upload_date" in doc
        assert doc["processing_status"] == "PENDING"
        
        # Process document
        process_document(doc["id"])

    # Verify independent company names per document (never forced to session ticker MSFT)
    doc_companies = {d["document_name"]: d["company_name"] for d in uploaded_docs}
    assert doc_companies["Apple_Q3_2024_Earnings_Call_Transcript.txt"] == "Apple Inc."
    assert doc_companies["Microsoft_FY2024_Form_10K_Annual_Report.txt"] == "Microsoft Corporation"
    assert doc_companies["Tesla_Financial_Performance_and_Deliveries.csv"] == "Tesla, Inc."

    # Verify document list with statuses
    list_res = client.get(f"/api/sessions/{session_id}/documents")
    assert list_res.status_code == 200
    docs = list_res.json()
    assert len(docs) == 4

    doc_types = {d["document_name"]: d["document_type"] for d in docs}
    assert doc_types["Apple_Q3_2024_Earnings_Call_Transcript.txt"] == "Earnings Call Transcript"
    assert doc_types["Microsoft_FY2024_Form_10K_Annual_Report.txt"] == "Form 10-K (Annual Report)"
    assert doc_types["Tesla_Financial_Performance_and_Deliveries.csv"] == "Financial Dataset / Metrics"
    assert "Form 10-K" in doc_types["Sample_Blank_Form_10K.pdf"]

    for d in docs:
        assert d["processing_status"] == "READY"
        assert d["page_count"] >= 1

    # Test detail and reprocessing
    pdf_doc = next(d for d in docs if d["document_name"] == "Sample_Blank_Form_10K.pdf")
    reprocess_res = client.post(f"/api/sessions/{session_id}/documents/{pdf_doc['id']}/reprocess")
    assert reprocess_res.status_code == 200
    assert reprocess_res.json()["processing_status"] == "PENDING"

    # Reprocess again
    process_document(pdf_doc["id"])
    detail_res = client.get(f"/api/sessions/{session_id}/documents/{pdf_doc['id']}")
    assert detail_res.status_code == 200
    assert detail_res.json()["processing_status"] == "READY"

    # Verify download endpoint
    dl_res = client.get(f"/api/sessions/{session_id}/documents/{pdf_doc['id']}/download")
    assert dl_res.status_code == 200
    assert len(dl_res.content) > 0

    # Clean up test session (verifying cascade delete of documents and chunks)
    client.delete(f"/api/sessions/{session_id}")

    # Verify documents are gone
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM financial_documents WHERE session_id = ?", (session_id,))
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 0


def test_independent_company_per_document_in_session():
    """Verify that in session 'TCS Financial Analysis', Cognizant PDF gets Cognizant company and TCS gets TCS."""
    import io
    import fitz

    # Create dummy Cognizant annual report PDF in-memory
    doc_cog = fitz.open()
    page1 = doc_cog.new_page()
    page1.insert_text((50, 100), "Cognizant Technology Solutions Corporation\nAnnual Report 2024\nRevenue: $19.4 Billion")
    cog_bytes = doc_cog.tobytes()
    doc_cog.close()

    # Create dummy TCS report PDF in-memory
    doc_tcs = fitz.open()
    page2 = doc_tcs.new_page()
    page2.insert_text((50, 100), "Tata Consultancy Services Limited\nIntegrated Annual Report 2024-25\nRevenue: Rs 240,893 crore")
    tcs_bytes = doc_tcs.tobytes()
    doc_tcs.close()

    # Create session named 'TCS Financial Analysis' with ticker 'TCS'
    session_res = client.post("/api/sessions", json={
        "name": "TCS Financial Analysis",
        "ticker": "TCS",
        "description": "Session for testing independent document company decoupling"
    })
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    try:
        # Upload Cognizant PDF
        upload1 = client.post(
            f"/api/sessions/{session_id}/documents",
            files=[("files", ("cognizant annual report.pdf", cog_bytes, "application/pdf"))]
        )
        assert upload1.status_code == 201
        doc1 = upload1.json()[0]

        # Upload TCS PDF
        upload2 = client.post(
            f"/api/sessions/{session_id}/documents",
            files=[("files", ("TCS Integrated Annual Report 2024-25.pdf", tcs_bytes, "application/pdf"))]
        )
        assert upload2.status_code == 201
        doc2 = upload2.json()[0]

        # Crucial assertions:
        # 1. cognizant annual report.pdf MUST be "Cognizant" (NOT "TCS" from session ticker or name!)
        assert doc1["company_name"] == "Cognizant"
        assert doc1["company_name"] != "TCS"
        assert doc1["company_name"] != "TCS Financial Analysis"

        # 2. TCS Integrated Annual Report 2024-25.pdf MUST be "Tata Consultancy Services"
        assert doc2["company_name"] == "Tata Consultancy Services"

        # 3. Verify in document listing
        docs_res = client.get(f"/api/sessions/{session_id}/documents")
        assert docs_res.status_code == 200
        listed_docs = docs_res.json()
        doc_map = {d["document_name"]: d["company_name"] for d in listed_docs}

        assert doc_map["cognizant annual report.pdf"] == "Cognizant"
        assert doc_map["TCS Integrated Annual Report 2024-25.pdf"] == "Tata Consultancy Services"

        # 4. Test PATCH update company name
        patch_res = client.patch(
            f"/api/sessions/{session_id}/documents/{doc1['id']}",
            json={"company_name": "Cognizant Technology Solutions"}
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["company_name"] == "Cognizant Technology Solutions"

    finally:
        client.delete(f"/api/sessions/{session_id}")

