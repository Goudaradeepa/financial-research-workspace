import re
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from database import get_db_connection
from extraction_agent import search_faiss_chunks

# Semantic sub-topic classification queries
SUB_TOPIC_QUERIES = {
    "revenue": {
        "pattern": r"\b(revenue|sales|top-line|turnover|receipts)\b",
        "vector_query": "total revenue net sales revenue growth revenues by segment",
        "metric_keys": ["revenue", "revenue_growth"]
    },
    "profit": {
        "pattern": r"\b(net profit|net income|earnings|bottom-line|profitability)\b",
        "vector_query": "net income net profit net earnings after taxes consolidated statements of operations",
        "metric_keys": ["net_profit", "eps"]
    },
    "margins": {
        "pattern": r"\b(margin|margins|operating margin|gross margin|profit margin)\b",
        "vector_query": "operating margin gross margin net margin percentage of revenue",
        "metric_keys": ["operating_margin", "net_profit_margin", "gross_margin"]
    },
    "operating_income": {
        "pattern": r"\b(operating profit|operating income|ebitda|ebit)\b",
        "vector_query": "operating profit operating income ebitda earnings before interest taxes",
        "metric_keys": ["operating_profit", "ebitda"]
    },
    "debt": {
        "pattern": r"\b(debt|leverage|borrowing|loans|liabilities)\b",
        "vector_query": "total debt long term debt commercial paper total liabilities",
        "metric_keys": ["total_debt", "total_liabilities"]
    },
    "cash_flow": {
        "pattern": r"\b(cash flow|fcf|free cash flow|liquidity|cash and cash equivalents)\b",
        "vector_query": "free cash flow cash generated from operating activities cash and cash equivalents",
        "metric_keys": ["free_cash_flow", "cash_equivalents"]
    },
    "auditor": {
        "pattern": r"\b(auditor|audit|opinion|qualification|accounting firm)\b",
        "vector_query": "independent auditor report opinion basis for qualified opinion material weakness",
        "metric_keys": []
    }
}

def decompose_question(query: str) -> List[Dict[str, Any]]:
    """Breaks complex question into logical sub-questions based on financial topics."""
    detected_topics = []
    lower_q = query.lower()

    for topic_key, cfg in SUB_TOPIC_QUERIES.items():
        if re.search(cfg["pattern"], lower_q, re.IGNORECASE):
            detected_topics.append({
                "topic": topic_key,
                "label": topic_key.replace("_", " ").title(),
                "vector_query": cfg["vector_query"],
                "metric_keys": cfg["metric_keys"]
            })

    if not detected_topics:
        # Default fallback to original query
        detected_topics.append({
            "topic": "general_research",
            "label": "General Analysis",
            "vector_query": query,
            "metric_keys": []
        })

    return detected_topics

def answer_financial_research_query(
    session_id: str,
    query: str,
    document_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes Research Agent:
    1. Understands question and breaks into sub-topics.
    2. Searches indexed document chunks in FAISS for grounded text.
    3. Retrieves structured metrics from SQLite for verified numerical grounding.
    4. Synthesizes findings with exact source page citations.
    5. Fallback: Returns explicit 'Insufficient evidence' if unsupported.
    6. Persists query to research_queries table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Identify target document(s)
    if document_id:
        cursor.execute("SELECT id, session_id, company_name, document_name, financial_metrics FROM financial_documents WHERE id = ?", (document_id,))
        docs = cursor.fetchall()
    else:
        cursor.execute("SELECT id, session_id, company_name, document_name, financial_metrics FROM financial_documents WHERE session_id = ?", (session_id,))
        docs = cursor.fetchall()

    if not docs:
        conn.close()
        return {
            "query": query,
            "sub_questions": [query],
            "findings": ["No indexed financial documents found in this research session."],
            "evidence": [],
            "answer": "Insufficient evidence: No financial documents are currently indexed in this research session.",
            "sources": [],
            "agent_used": "Research Agent"
        }

    sub_topics = decompose_question(query)
    sub_questions_labels = [f"Analysis of {t['label']}" for t in sub_topics]

    findings = []
    all_evidence = []
    sources = []
    seen_sources = set()

    for target_doc in docs:
        d_id = target_doc["id"]
        c_name = target_doc["company_name"] or "Company"
        d_name = target_doc["document_name"]

        # Parse metrics from document
        metrics_dict: Dict[str, Any] = {}
        if target_doc["financial_metrics"]:
            try:
                raw_m = json.loads(target_doc["financial_metrics"])
                if isinstance(raw_m, list):
                    for m in raw_m:
                        if isinstance(m, dict) and "metric_key" in m:
                            metrics_dict[m["metric_key"]] = m
            except Exception:
                pass

        for topic in sub_topics:
            topic_label = topic["label"]
            v_query = topic["vector_query"]
            raw_matched_chunks = search_faiss_chunks(d_id, v_query, top_k=2)

            # Apply semantic relevance threshold so unrelated general questions return Insufficient evidence
            min_score = 0.38 if topic["topic"] == "general_research" else 0.25
            matched_chunks = [c for c in raw_matched_chunks if c.get("similarity_score", 0.0) >= min_score]

            # Check if any structured metrics match this topic
            metric_facts = []
            for m_key in topic["metric_keys"]:
                m_obj = metrics_dict.get(m_key)
                if m_obj and m_obj.get("status") == "available" and m_obj.get("value") is not None:
                    fy_str = f" in {m_obj.get('financial_year')}" if m_obj.get("financial_year") else ""
                    unit_str = f" {m_obj.get('unit')}" if m_obj.get("unit") else ""
                    val_str = f"{m_obj.get('value')}{unit_str}"
                    p_num = m_obj.get("source_page")
                    metric_facts.append(f"{m_obj.get('metric_name')}: {val_str}{fy_str} (Page {p_num})")

                    if p_num and (d_id, p_num) not in seen_sources:
                        seen_sources.add((d_id, p_num))
                        sources.append({
                            "company_name": c_name,
                            "document_name": d_name,
                            "source_page": p_num,
                            "source_chunk_id": m_obj.get("source_chunk_id"),
                            "snippet": f"Verified metric: {m_obj.get('metric_name')} = {val_str}"
                        })

            if metric_facts:
                findings.append(f"{c_name} - {topic_label}: " + "; ".join(metric_facts))
            elif matched_chunks:
                top_chunk = matched_chunks[0]
                p_num = top_chunk["page_number"]
                chunk_snippet = top_chunk["content"][:280].strip()
                findings.append(f"{c_name} - {topic_label}: Grounded in filing text (Page {p_num})")

                if (d_id, p_num) not in seen_sources:
                    seen_sources.add((d_id, p_num))
                    sources.append({
                        "company_name": c_name,
                        "document_name": d_name,
                        "source_page": p_num,
                        "source_chunk_id": top_chunk["chunk_id"],
                        "snippet": chunk_snippet
                    })
            else:
                findings.append(f"{c_name} - {topic_label}: Insufficient evidence in the indexed documents.")

            # Record evidence snippets
            for c in matched_chunks:
                all_evidence.append({
                    "topic": topic_label,
                    "company_name": c_name,
                    "document_name": d_name,
                    "source_page": c["page_number"],
                    "source_chunk_id": c["chunk_id"],
                    "content": c["content"][:320]
                })

    # Construct synthesized answer
    all_insufficient = all("Insufficient evidence" in f for f in findings)
    if findings and not all_insufficient:
        answer_parts = [f"### Research Findings for: \"{query}\"\n"]
        for f in findings:
            answer_parts.append(f"- **{f}**")

        if sources:
            pages_cited = sorted(list({s['source_page'] for s in sources if s.get('source_page')}))
            answer_parts.append(f"\n*Source Citations: Verified against filing pages {', '.join(map(str, pages_cited))} from indexed documents.*")
        else:
            answer_parts.append("\n*Note: Insufficient evidence in the indexed documents to support additional conclusions.*")

        answer_text = "\n".join(answer_parts)
    else:
        answer_text = f"Insufficient evidence in the indexed documents to answer the requested research inquiry: \"{query}\"."

    # Persist in research_queries table
    now = datetime.utcnow().isoformat()
    query_id = str(uuid.uuid4())
    cursor.execute("""
    INSERT INTO research_queries (
        id, session_id, query_text, answer_text, agent_used, sources, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        query_id,
        session_id,
        query,
        answer_text,
        "Research Agent",
        json.dumps(sources),
        now
    ))
    conn.commit()
    conn.close()

    return {
        "query": query,
        "sub_questions": sub_questions_labels,
        "findings": findings,
        "evidence": all_evidence[:6],
        "answer": answer_text,
        "sources": sources,
        "agent_used": "Research Agent"
    }
