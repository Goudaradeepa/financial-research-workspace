import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from database import get_db_connection

def generate_document_report(document_id: str) -> Dict[str, Any]:
    """
    Executes the initial Report Agent implementation:
    1. Executive Summary (grounded synthesis of verified metrics and risks)
    2. Key Financials (Revenue, Revenue Growth, Net Profit, EPS, Debt, Margins, Cash Flow)
    3. Sources (verified filing page references)
    Persists report to 'generated_reports' table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, session_id, company_name, document_name, document_type, financial_metrics, page_count
    FROM financial_documents
    WHERE id = ?
    """, (document_id,))
    doc = cursor.fetchone()

    if not doc:
        conn.close()
        raise ValueError(f"Document {document_id} not found in database")

    session_id = doc["session_id"]
    company_name = doc["company_name"] or "Company"
    doc_name = doc["document_name"]
    doc_type = doc["document_type"]

    # Parse metrics
    metrics_list = []
    metrics_by_key = {}
    if doc["financial_metrics"]:
        try:
            parsed = json.loads(doc["financial_metrics"])
            if isinstance(parsed, list):
                metrics_list = parsed
                for m in parsed:
                    if isinstance(m, dict) and "metric_key" in m:
                        metrics_by_key[m["metric_key"]] = m
        except Exception:
            pass

    # Fetch red flags for inclusion in executive context
    cursor.execute("""
    SELECT title, severity, status, source_page FROM red_flags
    WHERE document_id = ? AND status = 'FLAGGED'
    """, (document_id,))
    active_flags = cursor.fetchall()

    # Build Key Financials list
    target_report_keys = [
        ("revenue", "Total Revenue"),
        ("revenue_growth", "Revenue Growth Rate"),
        ("operating_profit", "Operating Profit"),
        ("net_profit", "Net Profit"),
        ("eps", "Diluted EPS"),
        ("total_debt", "Total Debt"),
        ("operating_margin", "Operating Margin"),
        ("net_profit_margin", "Net Profit Margin"),
        ("free_cash_flow", "Free Cash Flow")
    ]

    key_financials = []
    sources = []
    seen_sources = set()

    for k, display_name in target_report_keys:
        m = metrics_by_key.get(k)
        if m and m.get("status") == "available" and m.get("value") is not None:
            key_financials.append({
                "metric_name": display_name,
                "value": m["value"],
                "unit": m.get("unit"),
                "fiscal_year": m.get("financial_year"),
                "source_page": m.get("source_page")
            })
            p = m.get("source_page")
            if p and (document_id, p) not in seen_sources:
                seen_sources.add((document_id, p))
                sources.append({
                    "company_name": company_name,
                    "document_name": doc_name,
                    "source_page": p,
                    "source_chunk_id": m.get("source_chunk_id"),
                    "snippet": f"{display_name} = {m['value']} {m.get('unit') or ''}"
                })
        else:
            key_financials.append({
                "metric_name": display_name,
                "value": None,
                "unit": None,
                "fiscal_year": None,
                "source_page": None
            })

    # Synthesize Executive Summary from verified metrics
    rev_item = metrics_by_key.get("revenue")
    profit_item = metrics_by_key.get("net_profit")
    op_margin_item = metrics_by_key.get("operating_margin")
    debt_item = metrics_by_key.get("total_debt")

    exec_summary_paragraphs = []
    summary_p1 = f"{company_name} financial performance analysis based on audited filing '{doc_name}' ({doc_type})."
    
    financial_highlights = []
    if rev_item and rev_item.get("status") == "available":
        financial_highlights.append(f"total revenue of {rev_item['value']} {rev_item.get('unit') or ''}")
    if profit_item and profit_item.get("status") == "available":
        financial_highlights.append(f"net profit of {profit_item['value']} {profit_item.get('unit') or ''}")
    if op_margin_item and op_margin_item.get("status") == "available":
        financial_highlights.append(f"an operating margin of {op_margin_item['value']}%")

    if financial_highlights:
        summary_p1 += " The entity reported " + ", ".join(financial_highlights) + "."
    exec_summary_paragraphs.append(summary_p1)

    if debt_item and debt_item.get("status") == "available":
        exec_summary_paragraphs.append(
            f"Balance sheet analysis reveals total outstanding debt obligations of {debt_item['value']} {debt_item.get('unit') or ''} "
            f"(Source: Page {debt_item.get('source_page', 'N/A')})."
        )

    if active_flags:
        flag_titles = [f['title'] for f in active_flags]
        exec_summary_paragraphs.append(
            f"Risk analysis identified {len(active_flags)} notable financial indicator(s): {', '.join(flag_titles)}."
        )
    else:
        exec_summary_paragraphs.append("No critical financial flags or adverse auditor qualifications were detected.")

    executive_summary = "\n\n".join(exec_summary_paragraphs)
    report_title = f"Executive Financial Report: {company_name}"
    now = datetime.utcnow().isoformat()
    report_id = str(uuid.uuid4())

    # Persist report
    cursor.execute("DELETE FROM generated_reports WHERE document_id = ?", (document_id,))
    cursor.execute("""
    INSERT INTO generated_reports (
        id, session_id, document_id, company_name, title, executive_summary,
        key_financials, sources, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report_id,
        session_id,
        document_id,
        company_name,
        report_title,
        executive_summary,
        json.dumps(key_financials),
        json.dumps(sources),
        now
    ))
    conn.commit()
    conn.close()

    return {
        "id": report_id,
        "session_id": session_id,
        "document_id": document_id,
        "company_name": company_name,
        "title": report_title,
        "executive_summary": executive_summary,
        "key_financials": key_financials,
        "sources": sources,
        "created_at": now
    }

def get_document_report(document_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an existing generated report for a document."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, session_id, document_id, company_name, title, executive_summary,
           key_financials, sources, created_at
    FROM generated_reports
    WHERE document_id = ?
    ORDER BY created_at DESC LIMIT 1
    """, (document_id,))
    r = cursor.fetchone()
    conn.close()

    if not r:
        return None

    return {
        "id": r["id"],
        "session_id": r["session_id"],
        "document_id": r["document_id"],
        "company_name": r["company_name"],
        "title": r["title"],
        "executive_summary": r["executive_summary"],
        "key_financials": json.loads(r["key_financials"]) if r["key_financials"] else [],
        "sources": json.loads(r["sources"]) if r["sources"] else [],
        "created_at": r["created_at"]
    }
