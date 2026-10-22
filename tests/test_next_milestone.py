import sys
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from database import get_db_connection
from red_flag_agent import analyze_red_flags, get_document_red_flags
from orchestrator import run_full_document_pipeline, get_document_agent_runs
from research_agent import answer_financial_research_query
from comparison_agent import compare_company_documents
from report_agent import generate_document_report, get_document_report

client = TestClient(app)

SEED_SESSION = "seed-session-flagship-reports"
AAPL_DOC = "seed-doc-aapl-10k"
MSFT_DOC = "seed-doc-msft-10k"

def test_red_flag_agent_on_seed_document():
    """Verifies Red Flag Agent detects risks, checks auditor opinion, and provides source page citations."""
    flags = analyze_red_flags(AAPL_DOC)
    assert len(flags) == 7

    flag_types = {f["flag_type"]: f for f in flags}
    assert "rising_debt" in flag_types
    assert "falling_operating_margins" in flag_types
    assert "falling_net_margins" in flag_types
    assert "significant_revenue_changes" in flag_types
    assert "significant_profit_changes" in flag_types
    assert "unusual_financial_patterns" in flag_types
    assert "auditor_qualifications" in flag_types

    # Every flag must have title, description, explanation, status
    for f in flags:
        assert f["title"]
        assert f["description"]
        assert f["explanation"]
        assert f["status"] in ["FLAGGED", "CLEAN", "INSUFFICIENT_EVIDENCE"]
        assert f["document_id"] == AAPL_DOC

    # Debt check should cite source page (Page 3 for Apple's balance sheet)
    debt_flag = flag_types["rising_debt"]
    assert debt_flag["source_page"] is not None
    assert any("106.6" in m for m in debt_flag["supporting_metrics"])

    # Auditor check should have evaluated the document
    audit_flag = flag_types["auditor_qualifications"]
    assert audit_flag["status"] in ["CLEAN", "FLAGGED", "INSUFFICIENT_EVIDENCE"]

    # Verify retrieval from database
    stored_flags = get_document_red_flags(AAPL_DOC)
    assert len(stored_flags) == 7

def test_multi_agent_orchestrator_execution():
    """Verifies orchestrator runs Document Agent -> Extraction Agent -> Red Flag Agent sequentially with audit trail."""
    # Test on existing seed document to verify audit logging and end-to-end execution
    result = run_full_document_pipeline(AAPL_DOC)
    assert result["status"] == "COMPLETED"
    assert result["document_agent"] == "COMPLETED"
    assert result["extraction_agent"] == "COMPLETED"
    assert result["red_flag_agent"] == "COMPLETED"

    # Verify audit trail in agent_runs table
    runs = get_document_agent_runs(AAPL_DOC)
    assert len(runs) >= 3
    agent_names = [r["agent_name"] for r in runs]
    assert "Document Agent" in agent_names
    assert "Extraction Agent" in agent_names
    assert "Red Flag Agent" in agent_names

    for r in runs:
        assert r["status"] == "COMPLETED"
        assert r["started_at"] is not None
        assert r["completed_at"] is not None
        assert r["output_summary"] is not None

def test_research_agent_multi_part_query():
    """Verifies Research Agent decomposes multi-part query, searches FAISS, and returns grounded citations."""
    query = "How did the company's revenue and net profit change, and what happened to its margins?"
    res = answer_financial_research_query(
        session_id=SEED_SESSION,
        query=query,
        document_id=AAPL_DOC
    )

    assert res["query"] == query
    assert len(res["sub_questions"]) >= 2
    assert len(res["findings"]) > 0
    assert "Revenue" in res["answer"]
    assert len(res["sources"]) > 0

    # Ensure source pages are strictly preserved
    for s in res["sources"]:
        assert s["source_page"] is not None
        assert s["source_page"] >= 1
        assert s["company_name"] is not None

def test_research_agent_insufficient_evidence_handling():
    """Verifies Research Agent reports 'Insufficient evidence' when query is completely unsupported."""
    res = answer_financial_research_query(
        session_id=SEED_SESSION,
        query="What is the company's space exploration rocket launch schedule?",
        document_id=AAPL_DOC
    )
    # Findings should cite insufficient evidence
    assert any("Insufficient evidence" in f for f in res["findings"]) or "Insufficient evidence" in res["answer"]

def test_comparison_agent_apple_vs_microsoft():
    """Verifies Comparison Agent generates side-by-side metric matrix without ranking bias."""
    comp = compare_company_documents(
        session_id=SEED_SESSION,
        document_ids=[AAPL_DOC, MSFT_DOC]
    )

    assert len(comp["companies"]) == 2
    assert len(comp["metrics_table"]) >= 10

    # Verify metrics table rows
    rev_row = next(r for r in comp["metrics_table"] if r["metric_key"] == "revenue")
    assert rev_row["metric_name"] == "Total Revenue"

    for c in comp["companies"]:
        c_val = rev_row["company_values"][c]
        assert c_val["value"] is not None
        assert c_val["status"] == "available"
        assert c_val["source_page"] is not None

    # Verify no subjective ranking
    summary = comp["executive_comparison"]
    assert "winner" not in summary.lower()
    assert "best" not in summary.lower()
    assert "Side-by-Side" in summary

def test_report_agent_initial_implementation():
    """Verifies Report Agent generates Executive Summary, Key Financials, and Sources strictly from verified data."""
    report = generate_document_report(AAPL_DOC)
    assert report["title"].startswith("Executive Financial Report:")
    assert "391" in report["executive_summary"] or "Apple" in report["executive_summary"]

    # Key Financials
    fin_keys = [f["metric_name"] for f in report["key_financials"]]
    assert "Total Revenue" in fin_keys
    assert "Net Profit" in fin_keys
    assert "Operating Margin" in fin_keys

    rev_fin = next(f for f in report["key_financials"] if f["metric_name"] == "Total Revenue")
    assert rev_fin["value"] == 391.0
    assert rev_fin["source_page"] == 2

    # Sources
    assert len(report["sources"]) > 0
    for src in report["sources"]:
        assert src["source_page"] is not None
        assert src["company_name"] == "Apple Inc. (AAPL)"

def test_chat_router_api():
    """Verifies Conversational Router routes appropriately to Comparison, Red Flag, and Research agents."""
    # 1. Clarification on greeting
    res_greet = client.post(f"/api/sessions/{SEED_SESSION}/chat", json={"message": "hi"})
    assert res_greet.status_code == 200
    assert res_greet.json()["intent"] == "clarification"
    assert res_greet.json()["suggested_queries"] is not None

    # 2. Comparison intent
    res_comp = client.post(f"/api/sessions/{SEED_SESSION}/chat", json={"message": "Compare Apple and Microsoft on revenue and debt"})
    assert res_comp.status_code == 200
    assert res_comp.json()["intent"] == "comparison"
    assert "Total Revenue" in res_comp.json()["answer"]

    # 3. Red flags intent
    res_flags = client.post(f"/api/sessions/{SEED_SESSION}/chat", json={"message": "What are the major red flags or risks?"})
    assert res_flags.status_code == 200
    assert res_flags.json()["intent"] == "red_flags"

    # 4. Research intent
    res_research = client.post(f"/api/sessions/{SEED_SESSION}/chat", json={"message": "What was Apple revenue and operating margin in FY2024?"})
    assert res_research.status_code == 200
    assert res_research.json()["intent"] == "research"
    assert len(res_research.json()["sources"]) > 0

def test_red_flags_and_reports_api_endpoints():
    """Verifies FastAPI endpoints for Red Flags and Reports."""
    # Red flags endpoint
    res_flags = client.get(f"/api/sessions/{SEED_SESSION}/documents/{AAPL_DOC}/red-flags")
    assert res_flags.status_code == 200
    assert len(res_flags.json()) == 7

    # Report endpoint
    res_rep = client.get(f"/api/sessions/{SEED_SESSION}/documents/{AAPL_DOC}/report")
    assert res_rep.status_code == 200
    assert "Executive Summary" in res_rep.json()["executive_summary"] or "Apple" in res_rep.json()["executive_summary"]
