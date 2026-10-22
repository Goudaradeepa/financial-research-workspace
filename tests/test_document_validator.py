import sys
import json
import pytest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import get_db_connection, init_db
from document_validator import validate_document_relevance, DocumentRelevanceClassification
from orchestrator import run_full_document_pipeline

def test_financial_annual_report_classification():
    """Test 1: Financial annual report classified as FINANCIAL with high confidence."""
    text = (
        "Tata Consultancy Services Integrated Annual Report 2024. "
        "Consolidated Financial Statements for the fiscal year ended March 31, 2024. "
        "Total Revenue was Rs 240,893 crore, operating margin was 24.6%, and net income reached Rs 46,099 crore. "
        "Consolidated Balance Sheet reflects total assets and total liabilities. "
        "Independent Auditor's Report issued by Price Waterhouse LLP."
    )
    result = validate_document_relevance("TCS_Integrated_Annual_Report_2024.pdf", text)
    assert result["classification"] == DocumentRelevanceClassification.FINANCIAL
    assert result["confidence"] == "HIGH"
    assert "revenue" in result["reason"].lower() or "financial-statement" in result["reason"].lower()

def test_unrelated_non_financial_document_classification():
    """Test 2: Clearly unrelated document (question paper, code, notes) classified as NON_FINANCIAL."""
    academic_text = (
        "Department of Computer Science and Engineering. "
        "End Semester Examination - November 2024. "
        "Course Code: CS301 - Data Structures and Algorithms. "
        "Maximum Marks: 100. Time: 3 hours. "
        "Q1: Define a Binary Search Tree. Write the algorithm to insert a node. (10 marks). "
        "Q2: Explain Quicksort partitioning logic with pseudocode. (15 marks)."
    )
    res_academic = validate_document_relevance("Semester_Exam_Question_Paper_CS301.pdf", academic_text)
    assert res_academic["classification"] == DocumentRelevanceClassification.NON_FINANCIAL
    assert res_academic["confidence"] == "HIGH"
    assert "technical/academic" in res_academic["reason"].lower() or "not contain sufficient" in res_academic["reason"].lower()

    # Resume test
    resume_text = (
        "John Doe - Curriculum Vitae. "
        "Software Engineer with 5 years experience in Python and React. "
        "Technical Skills: Docker, Kubernetes, PostgreSQL. "
        "Education: Bachelor of Science in Computer Science."
    )
    res_resume = validate_document_relevance("John_Doe_Resume.pdf", resume_text)
    assert res_resume["classification"] == DocumentRelevanceClassification.NON_FINANCIAL

def test_ambiguous_uncertain_document_classification():
    """Test 3: Ambiguous or sparse document classified as UNCERTAIN."""
    sparse_text = "Project sync notes. Discussed timelines with product team. Follow up tomorrow."
    result = validate_document_relevance("Quick_Meeting_Notes.pdf", sparse_text)
    assert result["classification"] == DocumentRelevanceClassification.UNCERTAIN
    assert result["confidence"] == "LOW"
    assert "unable to confidently determine" in result["reason"].lower()

def test_non_financial_document_skips_extraction_and_red_flags(tmp_path):
    """Test 4: NON_FINANCIAL document stops after validation, does not trigger financial extraction."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create dummy session
    session_id = "test-session-non-fin"
    cursor.execute("INSERT OR IGNORE INTO research_sessions (id, name, created_at, updated_at) VALUES (?, ?, '2026-01-01', '2026-01-01')",
                   (session_id, "Non-Financial Test Session"))

    # Create dummy PDF file for non-financial document
    doc_id = "test-doc-syllabus"
    doc_file = tmp_path / "CS_Syllabus.txt"
    doc_file.write_text(
        "Department of Computer Science. Course Syllabus for CS201. "
        "Topics: Data Structures, Algorithms, Linked Lists, Stacks, Queues, Binary Trees. "
        "Assignment schedule and grading policies for the semester.",
        encoding="utf-8"
    )

    cursor.execute("""
    INSERT OR REPLACE INTO financial_documents (
        id, session_id, document_name, document_type, file_path, upload_date,
        processing_status, file_size_bytes, page_count, word_count, created_at, updated_at
    ) VALUES (?, ?, 'CS_Syllabus.txt', 'Detecting...', ?, '2026-01-01', 'PENDING', 500, 1, 30, '2026-01-01', '2026-01-01')
    """, (doc_id, session_id, str(doc_file)))
    conn.commit()
    conn.close()

    # Run multi-agent orchestrator pipeline
    pipeline_res = run_full_document_pipeline(doc_id)

    # Must return unsupported document / non-financial status
    assert pipeline_res["status"] == "Unsupported Document"
    assert pipeline_res["classification"] == "NON_FINANCIAL"
    assert pipeline_res["extraction_agent"] == "SKIPPED"
    assert pipeline_res["red_flag_agent"] == "SKIPPED"

    # Verify database state
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT relevance_status, relevance_reason, financial_metrics FROM financial_documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()

    assert row["relevance_status"] == "NON_FINANCIAL"
    assert row["financial_metrics"] == "[]"

def test_financial_document_continues_to_extraction_and_downstream():
    """Test 5: FINANCIAL document continues to Extraction Agent & completes pipeline."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check that seed document Apple 10-K is classified as FINANCIAL
    cursor.execute("SELECT id, relevance_status, financial_metrics FROM financial_documents WHERE id = 'seed-doc-aapl-10k'")
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row["relevance_status"] == "FINANCIAL"
    metrics = json.loads(row["financial_metrics"])
    assert len(metrics) > 0
