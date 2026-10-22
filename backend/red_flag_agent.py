import re
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from database import get_db_connection
from extraction_agent import search_faiss_chunks

def analyze_red_flags(document_id: str) -> List[Dict[str, Any]]:
    """
    Executes the Red Flag Agent on a processed document:
    1. Fetches verified extracted financial metrics from SQLite.
    2. Runs systematic pattern checks:
       - Rising debt levels / High leverage
       - Falling / compressed operating margins
       - Falling / negative net profit margins
       - Significant revenue changes
       - Significant profit changes / Divergence
       - Unusual financial patterns (e.g. Free Cash Flow deficit)
       - Auditor qualifications / Internal control material weaknesses (via FAISS scan)
    3. Persists findings into the 'red_flags' table.
    4. Returns grounded red flag records with source citations.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, session_id, company_name, document_name, financial_metrics, page_count, relevance_status
    FROM financial_documents
    WHERE id = ?
    """, (document_id,))
    doc = cursor.fetchone()

    if not doc:
        conn.close()
        raise ValueError(f"Document {document_id} not found in database")

    if doc["relevance_status"] == "NON_FINANCIAL":
        conn.close()
        print(f"[RedFlagAgent] Skipping red flag analysis for non-financial document {document_id}.")
        return []

    session_id = doc["session_id"]
    company_name = doc["company_name"] or "Unknown Company"
    doc_name = doc["document_name"]
    raw_metrics_json = doc["financial_metrics"]

    # Parse extracted metrics
    metrics_map: Dict[str, Dict[str, Any]] = {}
    if raw_metrics_json:
        try:
            parsed = json.loads(raw_metrics_json)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "metric_key" in item:
                        metrics_map[item["metric_key"]] = item
        except Exception:
            pass

    flags: List[Dict[str, Any]] = []
    now = datetime.utcnow().isoformat()

    # Helper to get numeric metric value
    def get_num(key: str) -> Optional[float]:
        m = metrics_map.get(key)
        if m and m.get("status") == "available" and m.get("value") is not None:
            try:
                return float(m["value"])
            except (ValueError, TypeError):
                return None
        return None

    def get_metric_item(key: str) -> Optional[Dict[str, Any]]:
        return metrics_map.get(key)

    # -------------------------------------------------------------
    # Check 1: Rising Debt Levels / Excessive Leverage
    # -------------------------------------------------------------
    debt_item = get_metric_item("total_debt")
    assets_item = get_metric_item("total_assets")
    cash_item = get_metric_item("cash_equivalents")
    debt_val = get_num("total_debt")
    assets_val = get_num("total_assets")
    cash_val = get_num("cash_equivalents")

    if debt_val is not None:
        debt_fy = debt_item.get("financial_year")
        debt_page = debt_item.get("source_page")
        debt_chunk = debt_item.get("source_chunk_id")
        debt_unit = debt_item.get("unit") or "$B"

        supporting = [f"Total Debt: {debt_val} {debt_unit}"]
        if cash_val is not None:
            supporting.append(f"Cash & Equivalents: {cash_val} {cash_item.get('unit') or '$B'}")
        if assets_val is not None:
            supporting.append(f"Total Assets: {assets_val} {assets_item.get('unit') or '$B'}")

        # Search chunks for debt trend context
        debt_trend_chunks = search_faiss_chunks(document_id, "borrowings issued debt credit facility increased debt obligations", top_k=2)
        trend_evidence = debt_trend_chunks[0]["content"][:300] if debt_trend_chunks else None

        is_flagged = False
        reasons = []

        if assets_val is not None and assets_val > 0 and (debt_val / assets_val) > 0.60:
            is_flagged = True
            reasons.append(f"Debt-to-assets ratio is elevated at {round((debt_val / assets_val) * 100, 1)}% (>60% threshold)")

        if cash_val is not None and cash_val > 0 and (debt_val / cash_val) > 3.0:
            is_flagged = True
            reasons.append(f"Total debt exceeds liquid cash reserves by {round(debt_val / cash_val, 1)}x")

        if is_flagged:
            flags.append({
                "flag_type": "rising_debt",
                "title": "Elevated Debt & Leverage Exposure",
                "description": f"The company exhibits elevated debt exposure. {'; '.join(reasons)}.",
                "supporting_metrics": supporting,
                "fiscal_period": debt_fy,
                "severity": "HIGH" if (assets_val and (debt_val / assets_val) > 0.8) else "MEDIUM",
                "source_page": debt_page,
                "source_chunk_id": debt_chunk,
                "evidence_text": trend_evidence,
                "explanation": f"High debt burden can increase interest expense volatility and debt refinancing risks. Flagged based on extracted debt of {debt_val} {debt_unit}.",
                "status": "FLAGGED"
            })
        else:
            flags.append({
                "flag_type": "rising_debt",
                "title": "Debt Levels Manageable",
                "description": f"Total debt of {debt_val} {debt_unit} is well covered relative to assets and liquid reserves.",
                "supporting_metrics": supporting,
                "fiscal_period": debt_fy,
                "severity": "LOW",
                "source_page": debt_page,
                "source_chunk_id": debt_chunk,
                "evidence_text": trend_evidence,
                "explanation": "No disproportionate debt accumulation or leverage imbalance identified.",
                "status": "CLEAN"
            })
    else:
        flags.append({
            "flag_type": "rising_debt",
            "title": "Debt Levels: Insufficient Evidence",
            "description": "Total debt metric not reported or unavailable in extracted financial statements.",
            "supporting_metrics": ["Total Debt: Not Reported"],
            "fiscal_period": None,
            "severity": "INFO",
            "source_page": None,
            "source_chunk_id": None,
            "evidence_text": None,
            "explanation": "Insufficient evidence in the indexed document to evaluate debt trajectory.",
            "status": "INSUFFICIENT_EVIDENCE"
        })

    # -------------------------------------------------------------
    # Check 2: Falling / Compressed Operating Margins
    # -------------------------------------------------------------
    op_margin_item = get_metric_item("operating_margin")
    op_margin_val = get_num("operating_margin")

    if op_margin_val is not None:
        op_fy = op_margin_item.get("financial_year")
        op_page = op_margin_item.get("source_page")
        op_chunk = op_margin_item.get("source_chunk_id")
        supporting = [f"Operating Margin: {op_margin_val}%"]

        if op_margin_val < 0:
            flags.append({
                "flag_type": "falling_operating_margins",
                "title": "Negative Operating Margin (Operating Loss)",
                "description": f"Operating margin is negative at {op_margin_val}%, reflecting operational losses.",
                "supporting_metrics": supporting,
                "fiscal_period": op_fy,
                "severity": "HIGH",
                "source_page": op_page,
                "source_chunk_id": op_chunk,
                "evidence_text": None,
                "explanation": "Core operational revenue is insufficient to cover operating expenses.",
                "status": "FLAGGED"
            })
        elif op_margin_val < 10.0:
            flags.append({
                "flag_type": "falling_operating_margins",
                "title": "Compressed Operating Margin",
                "description": f"Operating margin is thin at {op_margin_val}% (<10% benchmark).",
                "supporting_metrics": supporting,
                "fiscal_period": op_fy,
                "severity": "MEDIUM",
                "source_page": op_page,
                "source_chunk_id": op_chunk,
                "evidence_text": None,
                "explanation": "Thin operating margin leaves little cushion against cost inflation or volume shocks.",
                "status": "FLAGGED"
            })
        else:
            flags.append({
                "flag_type": "falling_operating_margins",
                "title": "Operating Margin Robust",
                "description": f"Operating margin stands healthy at {op_margin_val}%.",
                "supporting_metrics": supporting,
                "fiscal_period": op_fy,
                "severity": "LOW",
                "source_page": op_page,
                "source_chunk_id": op_chunk,
                "evidence_text": None,
                "explanation": "Operating margin meets or exceeds healthy commercial baseline.",
                "status": "CLEAN"
            })
    else:
        flags.append({
            "flag_type": "falling_operating_margins",
            "title": "Operating Margin: Insufficient Evidence",
            "description": "Operating margin percentage not reported or unavailable in extracted financial data.",
            "supporting_metrics": ["Operating Margin: Not Reported"],
            "fiscal_period": None,
            "severity": "INFO",
            "source_page": None,
            "source_chunk_id": None,
            "evidence_text": None,
            "explanation": "Insufficient evidence in the indexed document to evaluate operating margin.",
            "status": "INSUFFICIENT_EVIDENCE"
        })

    # -------------------------------------------------------------
    # Check 3: Falling / Thin Net Profit Margins
    # -------------------------------------------------------------
    net_margin_item = get_metric_item("net_profit_margin")
    net_profit_item = get_metric_item("net_profit")
    net_margin_val = get_num("net_profit_margin")
    net_profit_val = get_num("net_profit")

    if net_margin_val is not None or net_profit_val is not None:
        val_for_eval = net_margin_val if net_margin_val is not None else 0.0
        nm_page = (net_margin_item or net_profit_item).get("source_page")
        nm_chunk = (net_margin_item or net_profit_item).get("source_chunk_id")
        nm_fy = (net_margin_item or net_profit_item).get("financial_year")
        supporting = []
        if net_margin_val is not None:
            supporting.append(f"Net Margin: {net_margin_val}%")
        if net_profit_val is not None:
            supporting.append(f"Net Profit: {net_profit_val} {(net_profit_item or {}).get('unit') or '$B'}")

        if net_profit_val is not None and net_profit_val < 0:
            flags.append({
                "flag_type": "falling_net_margins",
                "title": "Negative Net Profit Margin (Net Loss)",
                "description": f"The company reported a net loss of {net_profit_val} {(net_profit_item or {}).get('unit') or '$B'}.",
                "supporting_metrics": supporting,
                "fiscal_period": nm_fy,
                "severity": "HIGH",
                "source_page": nm_page,
                "source_chunk_id": nm_chunk,
                "evidence_text": None,
                "explanation": "Unprofitable bottom-line operations erode book equity value.",
                "status": "FLAGGED"
            })
        elif net_margin_val is not None and net_margin_val < 5.0:
            flags.append({
                "flag_type": "falling_net_margins",
                "title": "Subdued Net Profit Margin",
                "description": f"Net profit margin is compressed at {net_margin_val}% (<5% threshold).",
                "supporting_metrics": supporting,
                "fiscal_period": nm_fy,
                "severity": "MEDIUM",
                "source_page": nm_page,
                "source_chunk_id": nm_chunk,
                "evidence_text": None,
                "explanation": "Low net conversion leaves company vulnerable to tax, interest, or volume shifts.",
                "status": "FLAGGED"
            })
        else:
            flags.append({
                "flag_type": "falling_net_margins",
                "title": "Net Profit Margin Satisfactory",
                "description": f"Net profitability is positive ({supporting[0] if supporting else 'Profitable'}).",
                "supporting_metrics": supporting,
                "fiscal_period": nm_fy,
                "severity": "LOW",
                "source_page": nm_page,
                "source_chunk_id": nm_chunk,
                "evidence_text": None,
                "explanation": "No immediate net margin deterioration detected from extracted figures.",
                "status": "CLEAN"
            })
    else:
        flags.append({
            "flag_type": "falling_net_margins",
            "title": "Net Margin: Insufficient Evidence",
            "description": "Net profit margin and net income metrics unavailable in extracted data.",
            "supporting_metrics": ["Net Profit Margin: Not Reported"],
            "fiscal_period": None,
            "severity": "INFO",
            "source_page": None,
            "source_chunk_id": None,
            "evidence_text": None,
            "explanation": "Insufficient evidence to assess bottom-line profitability.",
            "status": "INSUFFICIENT_EVIDENCE"
        })

    # -------------------------------------------------------------
    # Check 4: Significant Revenue Changes
    # -------------------------------------------------------------
    rev_growth_item = get_metric_item("revenue_growth")
    rev_growth_val = get_num("revenue_growth")

    if rev_growth_val is not None:
        rg_fy = rev_growth_item.get("financial_year")
        rg_page = rev_growth_item.get("source_page")
        rg_chunk = rev_growth_item.get("source_chunk_id")
        supporting = [f"Revenue Growth: {rev_growth_val}%"]

        if rev_growth_val < -5.0:
            flags.append({
                "flag_type": "significant_revenue_changes",
                "title": "Negative Revenue Contraction",
                "description": f"Top-line revenue contracted significantly by {rev_growth_val}%.",
                "supporting_metrics": supporting,
                "fiscal_period": rg_fy,
                "severity": "HIGH",
                "source_page": rg_page,
                "source_chunk_id": rg_chunk,
                "evidence_text": None,
                "explanation": "Revenue decline indicates customer attrition, pricing pressure, or market share loss.",
                "status": "FLAGGED"
            })
        elif rev_growth_val > 50.0:
            flags.append({
                "flag_type": "significant_revenue_changes",
                "title": "Hyper Revenue Expansion",
                "description": f"Top-line growth surged by {rev_growth_val}%, warranting inspection of sustainability.",
                "supporting_metrics": supporting,
                "fiscal_period": rg_fy,
                "severity": "INFO",
                "source_page": rg_page,
                "source_chunk_id": rg_chunk,
                "evidence_text": None,
                "explanation": "Rapid revenue scaling flagged for organic vs inorganic composition analysis.",
                "status": "FLAGGED"
            })
        else:
            flags.append({
                "flag_type": "significant_revenue_changes",
                "title": "Revenue Growth Steady",
                "description": f"Revenue growth of {rev_growth_val}% indicates stable top-line trajectory.",
                "supporting_metrics": supporting,
                "fiscal_period": rg_fy,
                "severity": "LOW",
                "source_page": rg_page,
                "source_chunk_id": rg_chunk,
                "evidence_text": None,
                "explanation": "Revenue trajectory is within standard organic expansion ranges.",
                "status": "CLEAN"
            })
    else:
        flags.append({
            "flag_type": "significant_revenue_changes",
            "title": "Revenue Growth: Insufficient Evidence",
            "description": "Year-over-year revenue growth rate not directly extracted.",
            "supporting_metrics": ["Revenue Growth: Not Reported"],
            "fiscal_period": None,
            "severity": "INFO",
            "source_page": None,
            "source_chunk_id": None,
            "evidence_text": None,
            "explanation": "Insufficient evidence to determine top-line percentage trend.",
            "status": "INSUFFICIENT_EVIDENCE"
        })

    # -------------------------------------------------------------
    # Check 5: Significant Profit Changes / Divergence
    # -------------------------------------------------------------
    net_profit_val = get_num("net_profit")
    rev_growth_val = get_num("revenue_growth")
    op_profit_val = get_num("operating_profit")

    if rev_growth_val is not None and net_profit_val is not None:
        supporting = [f"Revenue Growth: {rev_growth_val}%", f"Net Profit: {net_profit_val}"]
        if rev_growth_val > 10.0 and net_profit_val <= 0:
            flags.append({
                "flag_type": "significant_profit_changes",
                "title": "Revenue & Profit Divergence (Unprofitable Growth)",
                "description": f"Revenue expanded ({rev_growth_val}%) while net profit was zero or negative ({net_profit_val}).",
                "supporting_metrics": supporting,
                "fiscal_period": (net_profit_item or {}).get("financial_year"),
                "severity": "HIGH",
                "source_page": (net_profit_item or {}).get("source_page"),
                "source_chunk_id": (net_profit_item or {}).get("source_chunk_id"),
                "evidence_text": None,
                "explanation": "Expanding sales without corresponding profitability reflects structural margin deficit.",
                "status": "FLAGGED"
            })
        else:
            flags.append({
                "flag_type": "significant_profit_changes",
                "title": "Profit Trajectory Aligned",
                "description": f"Profit metrics align consistently with business volume.",
                "supporting_metrics": supporting,
                "fiscal_period": (net_profit_item or {}).get("financial_year"),
                "severity": "LOW",
                "source_page": (net_profit_item or {}).get("source_page"),
                "source_chunk_id": (net_profit_item or {}).get("source_chunk_id"),
                "evidence_text": None,
                "explanation": "No destructive divergence between top-line expansion and bottom-line earnings.",
                "status": "CLEAN"
            })
    else:
        flags.append({
            "flag_type": "significant_profit_changes",
            "title": "Profit Divergence: Insufficient Evidence",
            "description": "Comparative growth and profit metrics missing for simultaneous cross-analysis.",
            "supporting_metrics": ["Profit Growth: Not Reported"],
            "fiscal_period": None,
            "severity": "INFO",
            "source_page": None,
            "source_chunk_id": None,
            "evidence_text": None,
            "explanation": "Insufficient multi-year metrics extracted to verify divergence.",
            "status": "INSUFFICIENT_EVIDENCE"
        })

    # -------------------------------------------------------------
    # Check 6: Unusual Financial Patterns (Free Cash Flow Quality)
    # -------------------------------------------------------------
    fcf_item = get_metric_item("free_cash_flow")
    fcf_val = get_num("free_cash_flow")

    if fcf_val is not None:
        fcf_page = fcf_item.get("source_page")
        fcf_chunk = fcf_item.get("source_chunk_id")
        fcf_fy = fcf_item.get("financial_year")
        fcf_unit = fcf_item.get("unit") or "$B"
        supporting = [f"Free Cash Flow: {fcf_val} {fcf_unit}"]

        if fcf_val < 0:
            flags.append({
                "flag_type": "unusual_financial_patterns",
                "title": "Negative Free Cash Flow (Cash Burn)",
                "description": f"Free cash flow is negative at {fcf_val} {fcf_unit}, indicating cash burn.",
                "supporting_metrics": supporting,
                "fiscal_period": fcf_fy,
                "severity": "HIGH",
                "source_page": fcf_page,
                "source_chunk_id": fcf_chunk,
                "evidence_text": None,
                "explanation": "Company consumed more cash in operations and capex than it generated.",
                "status": "FLAGGED"
            })
        else:
            flags.append({
                "flag_type": "unusual_financial_patterns",
                "title": "Positive Free Cash Flow Generation",
                "description": f"Company generated solid free cash flow of {fcf_val} {fcf_unit}.",
                "supporting_metrics": supporting,
                "fiscal_period": fcf_fy,
                "severity": "LOW",
                "source_page": fcf_page,
                "source_chunk_id": fcf_chunk,
                "evidence_text": None,
                "explanation": "Cash conversion from reported operations remains self-funding.",
                "status": "CLEAN"
            })
    else:
        flags.append({
            "flag_type": "unusual_financial_patterns",
            "title": "Cash Flow Pattern: Insufficient Evidence",
            "description": "Free cash flow metric was not extracted or reported.",
            "supporting_metrics": ["Free Cash Flow: Not Reported"],
            "fiscal_period": None,
            "severity": "INFO",
            "source_page": None,
            "source_chunk_id": None,
            "evidence_text": None,
            "explanation": "Insufficient evidence in document extracts to confirm free cash flow quality.",
            "status": "INSUFFICIENT_EVIDENCE"
        })

    # -------------------------------------------------------------
    # Check 7: Auditor Qualifications & Internal Controls
    # -------------------------------------------------------------
    # Search document chunks for independent auditor report
    audit_chunks = search_faiss_chunks(
        document_id,
        "Report of Independent Registered Public Accounting Firm opinion basis for qualified opinion material weakness going concern",
        top_k=4
    )

    found_audit_flag = False
    audit_flag_item = None

    if audit_chunks:
        # Scan for explicit qualifications
        qual_pattern = re.compile(
            r"\b(qualified opinion|adverse opinion|disclaimer of opinion|except for the effects|material weakness in internal control|substantial doubt about.*going concern)\b",
            re.IGNORECASE
        )
        clean_pattern = re.compile(
            r"\b(present fairly, in all material respects|unqualified opinion|in our opinion, the consolidated financial statements present fairly)\b",
            re.IGNORECASE
        )

        for c in audit_chunks:
            text = c["content"]
            m_qual = qual_pattern.search(text)
            if m_qual:
                found_audit_flag = True
                snippet = text[max(0, m_qual.start() - 100):min(len(text), m_qual.end() + 150)].strip()
                audit_flag_item = {
                    "flag_type": "auditor_qualifications",
                    "title": "Auditor Qualification / Material Weakness Detected",
                    "description": f"The Independent Auditor report contains non-standard language: '{m_qual.group(0)}'.",
                    "supporting_metrics": ["Audit Report: Qualified / Non-standard"],
                    "fiscal_period": None,
                    "severity": "HIGH",
                    "source_page": c["page_number"],
                    "source_chunk_id": c["chunk_id"],
                    "evidence_text": snippet,
                    "explanation": "Auditor reservations or internal control deficiencies significantly impair reported financial reliability.",
                    "status": "FLAGGED"
                }
                break

        if not found_audit_flag:
            # Check for clean confirmation
            for c in audit_chunks:
                text = c["content"]
                m_clean = clean_pattern.search(text)
                if m_clean:
                    snippet = text[max(0, m_clean.start() - 60):min(len(text), m_clean.end() + 120)].strip()
                    audit_flag_item = {
                        "flag_type": "auditor_qualifications",
                        "title": "Independent Auditor Report: Unqualified (Clean)",
                        "description": "Auditor confirmed financial statements 'present fairly, in all material respects'.",
                        "supporting_metrics": ["Audit Opinion: Unqualified (Clean)"],
                        "fiscal_period": None,
                        "severity": "INFO",
                        "source_page": c["page_number"],
                        "source_chunk_id": c["chunk_id"],
                        "evidence_text": snippet,
                        "explanation": "Audit report confirmed free of material qualifications or going-concern modifications.",
                        "status": "CLEAN"
                    }
                    break

    if audit_flag_item:
        flags.append(audit_flag_item)
    else:
        flags.append({
            "flag_type": "auditor_qualifications",
            "title": "Auditor Report: Insufficient Evidence",
            "description": "Specific independent auditor report text not found in indexed document chunks.",
            "supporting_metrics": ["Audit Report: Not Found in Index Chunks"],
            "fiscal_period": None,
            "severity": "INFO",
            "source_page": None,
            "source_chunk_id": None,
            "evidence_text": None,
            "explanation": "Insufficient evidence in indexed chunks to verify auditor opinion status.",
            "status": "INSUFFICIENT_EVIDENCE"
        })

    # -------------------------------------------------------------
    # Persist findings to 'red_flags' table
    # -------------------------------------------------------------
    cursor.execute("DELETE FROM red_flags WHERE document_id = ?", (document_id,))
    final_output = []

    for f in flags:
        flag_id = str(uuid.uuid4())
        cursor.execute("""
        INSERT INTO red_flags (
            id, session_id, document_id, company_name, flag_type, title, description,
            supporting_metrics, fiscal_period, severity, source_page, source_chunk_id,
            evidence_text, explanation, status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            flag_id,
            session_id,
            document_id,
            company_name,
            f["flag_type"],
            f["title"],
            f["description"],
            json.dumps(f["supporting_metrics"]),
            f["fiscal_period"],
            f["severity"],
            f["source_page"],
            f["source_chunk_id"],
            f["evidence_text"],
            f["explanation"],
            f["status"],
            now
        ))

        f_copy = dict(f)
        f_copy["id"] = flag_id
        f_copy["session_id"] = session_id
        f_copy["document_id"] = document_id
        f_copy["company_name"] = company_name
        f_copy["created_at"] = now
        final_output.append(f_copy)

    conn.commit()
    conn.close()

    flagged_count = sum(1 for f in final_output if f["status"] == "FLAGGED")
    print(f"[RedFlagAgent] Analyzed doc {document_id} ({company_name}): {flagged_count} flagged risks, {len(final_output)} checks.")
    return final_output

def get_document_red_flags(document_id: str) -> List[Dict[str, Any]]:
    """Retrieves stored red flags for a document from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, session_id, document_id, company_name, flag_type, title, description,
           supporting_metrics, fiscal_period, severity, source_page, source_chunk_id,
           evidence_text, explanation, status, created_at
    FROM red_flags
    WHERE document_id = ?
    ORDER BY CASE severity WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 WHEN 'LOW' THEN 3 ELSE 4 END
    """, (document_id,))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "session_id": r["session_id"],
            "document_id": r["document_id"],
            "company_name": r["company_name"],
            "flag_type": r["flag_type"],
            "title": r["title"],
            "description": r["description"],
            "supporting_metrics": json.loads(r["supporting_metrics"]) if r["supporting_metrics"] else [],
            "fiscal_period": r["fiscal_period"],
            "severity": r["severity"],
            "source_page": r["source_page"],
            "source_chunk_id": r["source_chunk_id"],
            "evidence_text": r["evidence_text"],
            "explanation": r["explanation"],
            "status": r["status"],
            "created_at": r["created_at"]
        })
    return results

def get_session_red_flags(session_id: str) -> List[Dict[str, Any]]:
    """Retrieves all stored red flags across all documents in a session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, session_id, document_id, company_name, flag_type, title, description,
           supporting_metrics, fiscal_period, severity, source_page, source_chunk_id,
           evidence_text, explanation, status, created_at
    FROM red_flags
    WHERE session_id = ?
    ORDER BY CASE severity WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 WHEN 'LOW' THEN 3 ELSE 4 END
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "session_id": r["session_id"],
            "document_id": r["document_id"],
            "company_name": r["company_name"],
            "flag_type": r["flag_type"],
            "title": r["title"],
            "description": r["description"],
            "supporting_metrics": json.loads(r["supporting_metrics"]) if r["supporting_metrics"] else [],
            "fiscal_period": r["fiscal_period"],
            "severity": r["severity"],
            "source_page": r["source_page"],
            "source_chunk_id": r["source_chunk_id"],
            "evidence_text": r["evidence_text"],
            "explanation": r["explanation"],
            "status": r["status"],
            "created_at": r["created_at"]
        })
    return results
