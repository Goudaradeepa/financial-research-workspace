import json
from typing import List, Dict, Any, Optional

from database import get_db_connection

COMPARISON_METRIC_CONFIGS = [
    {"key": "revenue", "name": "Total Revenue", "default_unit": "$B"},
    {"key": "revenue_growth", "name": "Revenue Growth Rate", "default_unit": "%"},
    {"key": "operating_profit", "name": "Operating Profit / Income", "default_unit": "$B"},
    {"key": "net_profit", "name": "Net Profit / Income", "default_unit": "$B"},
    {"key": "ebitda", "name": "EBITDA", "default_unit": "$B"},
    {"key": "operating_margin", "name": "Operating Margin", "default_unit": "%"},
    {"key": "net_profit_margin", "name": "Net Profit Margin", "default_unit": "%"},
    {"key": "eps", "name": "Diluted Earnings Per Share (EPS)", "default_unit": "$/share"},
    {"key": "total_assets", "name": "Total Assets", "default_unit": "$B"},
    {"key": "total_liabilities", "name": "Total Liabilities", "default_unit": "$B"},
    {"key": "total_debt", "name": "Total Debt", "default_unit": "$B"},
    {"key": "cash_equivalents", "name": "Cash & Cash Equivalents", "default_unit": "$B"},
    {"key": "free_cash_flow", "name": "Free Cash Flow", "default_unit": "$B"},
    {"key": "gross_margin", "name": "Gross Margin", "default_unit": "%"}
]

def compare_company_documents(
    session_id: str,
    document_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Executes the Comparison Agent:
    1. Fetches extracted metrics for target documents from SQLite.
    2. Builds a side-by-side comparative matrix.
    3. Handles missing metrics as 'Not Reported' with strict source page preservation.
    4. Generates a neutral, factual executive comparison without subjective rankings.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if document_ids and len(document_ids) > 0:
        placeholders = ",".join(["?"] * len(document_ids))
        cursor.execute(f"""
        SELECT id, session_id, company_name, document_name, financial_metrics
        FROM financial_documents
        WHERE id IN ({placeholders}) AND session_id = ?
        """, (*document_ids, session_id))
    else:
        cursor.execute("""
        SELECT id, session_id, company_name, document_name, financial_metrics
        FROM financial_documents
        WHERE session_id = ?
        """, (session_id,))

    docs = cursor.fetchall()
    conn.close()

    if not docs:
        return {
            "session_id": session_id,
            "companies": [],
            "documents": [],
            "metrics_table": [],
            "executive_comparison": "Insufficient documents available in this session for comparison."
        }

    # Map each document's metrics
    doc_metadata_list = []
    company_metrics_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
    company_names = []

    for d in docs:
        c_name = d["company_name"] or d["document_name"]
        company_names.append(c_name)
        doc_metadata_list.append({
            "document_id": d["id"],
            "company_name": c_name,
            "document_name": d["document_name"]
        })

        metrics_for_company: Dict[str, Dict[str, Any]] = {}
        if d["financial_metrics"]:
            try:
                raw_list = json.loads(d["financial_metrics"])
                if isinstance(raw_list, list):
                    for item in raw_list:
                        if isinstance(item, dict) and "metric_key" in item:
                            metrics_for_company[item["metric_key"]] = item
            except Exception:
                pass
        company_metrics_map[c_name] = metrics_for_company

    # Build comparison rows
    comparison_rows = []
    for cfg in COMPARISON_METRIC_CONFIGS:
        m_key = cfg["key"]
        m_name = cfg["name"]
        company_vals: Dict[str, Dict[str, Any]] = {}

        num_vals = []
        for c_name in company_names:
            c_metrics = company_metrics_map.get(c_name, {})
            m_item = c_metrics.get(m_key)

            if m_item and m_item.get("status") == "available" and m_item.get("value") is not None:
                val = m_item.get("value")
                unit = m_item.get("unit") or cfg["default_unit"]
                fy = m_item.get("financial_year")
                src_page = m_item.get("source_page")
                company_vals[c_name] = {
                    "value": val,
                    "unit": unit,
                    "fiscal_year": fy,
                    "source_page": src_page,
                    "status": "available"
                }
                try:
                    num_vals.append((c_name, float(val), unit))
                except (ValueError, TypeError):
                    pass
            else:
                company_vals[c_name] = {
                    "value": None,
                    "unit": None,
                    "fiscal_year": None,
                    "source_page": None,
                    "status": "unavailable",
                    "display": "Not Reported"
                }

        diff_note = None
        if len(num_vals) == 2 and num_vals[0][2] == num_vals[1][2]:
            c1, v1, u = num_vals[0]
            c2, v2, _ = num_vals[1]
            diff = round(abs(v1 - v2), 2)
            higher = c1 if v1 > v2 else c2
            diff_note = f"{higher} reported higher by {diff} {u}."

        comparison_rows.append({
            "metric_name": m_name,
            "metric_key": m_key,
            "company_values": company_vals,
            "difference_note": diff_note
        })

    # Generate neutral executive summary
    comp_bullets = []
    for r in comparison_rows:
        if r.get("difference_note"):
            comp_bullets.append(f"- **{r['metric_name']}**: {r['difference_note']}")

    if comp_bullets:
        executive_summary = (
            f"### Side-by-Side Financial Comparison ({', '.join(company_names)})\n\n"
            + "\n".join(comp_bullets[:5])
            + "\n\n*Note: All figures are extracted directly from verified annual report filings with corresponding source page citations. Missing figures are designated as 'Not Reported'.*"
        )
    else:
        executive_summary = (
            f"Factual side-by-side metric comparison across {len(company_names)} documents. "
            "Metrics are sourced directly from indexed filings."
        )

    return {
        "session_id": session_id,
        "companies": company_names,
        "documents": doc_metadata_list,
        "metrics_table": comparison_rows,
        "executive_comparison": executive_summary
    }
