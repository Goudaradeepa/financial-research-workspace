import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import faiss

from database import get_db_connection, STORAGE_DIR
from document_agent import get_embedding_model, VECTOR_DIR

TARGET_METRICS = [
    {
        "key": "revenue",
        "name": "Total Revenue",
        "query": "total revenue net sales revenues",
        "patterns": [
            r"(?:total\s+revenue|net\s+sales|revenues?)\s*(?:was|of|were|totaled)?\s*[:$]?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|b|m)?",
            r"revenue\s*\(?\$?m?\)?\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)",
        ],
        "default_unit": "$B"
    },
    {
        "key": "revenue_growth",
        "name": "Revenue Growth Rate",
        "query": "revenue growth percentage increase year-over-year",
        "patterns": [
            r"(?:revenue|sales)\s+(?:growth|increased|grew|up)\s*(?:by|of)?\s*([0-9]+(?:\.[0-9]+)?)\s*%",
            r"yoy_growth_pct.*?([0-9]+(?:\.[0-9]+)?)\s*%",
            r"up\s*([0-9]+(?:\.[0-9]+)?)\s*%\s*(?:year-over-year|from\s+a\s+year\s+ago)",
            r"increase\s+of\s+([0-9]+(?:\.[0-9]+)?)\s*%"
        ],
        "default_unit": "%"
    },
    {
        "key": "operating_profit",
        "name": "Operating Profit / Income",
        "query": "operating income operating profit earnings from operations",
        "patterns": [
            r"(?:operating\s+income|operating\s+profit)\s*(?:was|of|were|totaled)?\s*[:$]?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|b|m)?",
            r"operating\s+income.*?\$?\s*([0-9]+(?:\.[0-9]+)?)"
        ],
        "default_unit": "$B"
    },
    {
        "key": "net_profit",
        "name": "Net Profit / Income",
        "query": "net income net profit net earnings after taxes",
        "patterns": [
            r"(?:net\s+income|net\s+profit|net\s+earnings)\s*(?:was|of|were|totaled)?\s*[:$]?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|b|m)?",
            r"net\s+income.*?\$?\s*([0-9]+(?:\.[0-9]+)?)"
        ],
        "default_unit": "$B"
    },
    {
        "key": "ebitda",
        "name": "EBITDA",
        "query": "ebitda earnings before interest taxes depreciation amortization",
        "patterns": [
            r"\bebitda\s*(?:was|of|were|totaled)?\s*[:$]?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|b|m)?",
            r"adjusted\s+ebitda.*?\$?\s*([0-9]+(?:\.[0-9]+)?)"
        ],
        "default_unit": "$B"
    },
    {
        "key": "operating_margin",
        "name": "Operating Margin",
        "query": "operating margin percentage of revenue",
        "patterns": [
            r"(?:operating\s+margin)\s*(?:was|of|were|at)?\s*[:]?\s*([0-9]+(?:\.[0-9]+)?)\s*%",
            r"operating\s+margin\s*\(%\)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*%"
        ],
        "default_unit": "%"
    },
    {
        "key": "net_profit_margin",
        "name": "Net Profit Margin",
        "query": "net margin net profit margin percentage",
        "patterns": [
            r"(?:net\s+(?:profit\s+)?margin)\s*(?:was|of|were|at)?\s*[:]?\s*([0-9]+(?:\.[0-9]+)?)\s*%"
        ],
        "default_unit": "%"
    },
    {
        "key": "eps",
        "name": "Diluted Earnings Per Share (EPS)",
        "query": "diluted earnings per share eps per share diluted",
        "patterns": [
            r"(?:diluted\s+(?:earnings\s+per\s+share|eps)|eps)\s*(?:was|of|were|at)?\s*[:$]?\s*([0-9]+(?:\.[0-9]+)?)",
            r"diluted\s+eps\s*(?:was)?\s*\$?\s*([0-9]+(?:\.[0-9]+)?)"
        ],
        "default_unit": "$/share"
    },
    {
        "key": "total_assets",
        "name": "Total Assets",
        "query": "consolidated balance sheet total assets",
        "patterns": [
            r"total\s+assets\s*(?:were|was|of|totaled)?\s*[:$]?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|b|m)?",
            r"assets\s+total.*?\$?\s*([0-9]+(?:\.[0-9]+)?)"
        ],
        "default_unit": "$B"
    },
    {
        "key": "total_liabilities",
        "name": "Total Liabilities",
        "query": "consolidated balance sheet total liabilities",
        "patterns": [
            r"total\s+liabilities\s*(?:were|was|of|totaled)?\s*[:$]?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|b|m)?",
            r"liabilities\s+total.*?\$?\s*([0-9]+(?:\.[0-9]+)?)"
        ],
        "default_unit": "$B"
    },
    {
        "key": "total_debt",
        "name": "Total Debt",
        "query": "total debt long term debt short term borrowings notes payable",
        "patterns": [
            r"(?:total\s+debt|aggregate\s+debt|long-term\s+debt)\s*(?:was|of|were|totaled)?\s*[:$]?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|b|m)?",
            r"debt.*?\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million)?"
        ],
        "default_unit": "$B"
    },
    {
        "key": "cash",
        "name": "Cash & Cash Equivalents",
        "query": "cash and cash equivalents marketable securities liquid funds",
        "patterns": [
            r"cash\s+(?:and\s+cash\s+equivalents|equivalents|and\s+marketable\s+securities)\s*(?:were|was|of|totaled)?\s*[:$]?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|b|m)?",
            r"cash\s*[:=]\s*\$?([0-9]+(?:\.[0-9]+)?)"
        ],
        "default_unit": "$B"
    },
    {
        "key": "free_cash_flow",
        "name": "Free Cash Flow",
        "query": "free cash flow operating cash flow capital expenditures",
        "patterns": [
            r"free\s+cash\s+flow\s*(?:was|of|were|totaled)?\s*[:$]?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|b|m)?"
        ],
        "default_unit": "$B"
    },
    {
        "key": "gross_margin",
        "name": "Gross Margin",
        "query": "gross margin gross profit percentage of sales",
        "patterns": [
            r"gross\s+margin\s*(?:was|of|were|at)?\s*[:]?\s*([0-9]+(?:\.[0-9]+)?)\s*%"
        ],
        "default_unit": "%"
    }
]

def search_faiss_chunks(doc_id: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Searches the document's FAISS index for the most semantically relevant chunks.
    Returns list of chunks with chunk_id, page_number, content, distance score.
    """
    index_path = VECTOR_DIR / f"{doc_id}.faiss"
    meta_path = VECTOR_DIR / f"{doc_id}_meta.json"

    if not index_path.exists() or not meta_path.exists():
        return []

    try:
        index = faiss.read_index(str(index_path))
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        if index.ntotal == 0 or len(metadata) == 0:
            return []

        model = get_embedding_model()
        q_embed = list(model.embed([query]))
        q_arr = np.array(q_embed).astype("float32")
        faiss.normalize_L2(q_arr)

        k = min(top_k, index.ntotal)
        distances, indices = index.search(q_arr, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(metadata):
                continue
            meta = metadata[idx]
            results.append({
                "chunk_id": meta["chunk_id"],
                "page_number": meta["page_number"],
                "content": meta["content"],
                "similarity_score": float(dist)
            })

        return results
    except Exception as e:
        print(f"Error searching FAISS for doc {doc_id}: {e}")
        return []

def extract_metric_from_chunks(metric_cfg: Dict[str, Any], candidate_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extracts structured metric from candidate chunks using regex.
    Strictly avoids inventing values. Returns available metric or null.
    """
    for chunk in candidate_chunks:
        text = chunk["content"]
        for pat in metric_cfg["patterns"]:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                val_str = match.group(1)
                try:
                    val_num = float(val_str)
                except ValueError:
                    val_num = val_str

                # Determine unit
                unit = metric_cfg["default_unit"]
                if len(match.groups()) >= 2 and match.group(2):
                    scale = match.group(2).lower()
                    if "b" in scale:
                        unit = "$B"
                    elif "m" in scale:
                        unit = "$M"
                elif "%" in pat:
                    unit = "%"
                elif "eps" in metric_cfg["key"]:
                    unit = "$/share"

                # Detect financial year in chunk if available
                year_match = re.search(r"\b(?:FY\s*20\d\d|Q[1-4]\s*20\d\d|20\d\d)\b", text, re.IGNORECASE)
                fy = year_match.group(0).upper() if year_match else None

                return {
                    "metric_name": metric_cfg["name"],
                    "metric_key": metric_cfg["key"],
                    "value": val_num,
                    "unit": unit,
                    "financial_year": fy,
                    "source_page": chunk["page_number"],
                    "source_chunk_id": chunk["chunk_id"],
                    "status": "available",
                    "confidence": "high"
                }

    # Not found in document: strictly return null (do not invent values)
    return {
        "metric_name": metric_cfg["name"],
        "metric_key": metric_cfg["key"],
        "value": None,
        "unit": None,
        "financial_year": None,
        "source_page": None,
        "source_chunk_id": None,
        "status": "unavailable",
        "confidence": "none"
    }

def extract_all_financial_metrics(document_id: str) -> List[Dict[str, Any]]:
    """
    Executes Extraction Agent for an indexed document:
    Retrieves relevant chunks via FAISS vector search, extracts 
    metrics with page numbers and chunk IDs, and stores in database.
    """
    extracted_metrics = []

    for metric_cfg in TARGET_METRICS:
        candidates = search_faiss_chunks(document_id, metric_cfg["query"], top_k=3)
        res = extract_metric_from_chunks(metric_cfg, candidates)
        extracted_metrics.append(res)

    # Persist extracted metrics into database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE financial_documents
    SET financial_metrics = ?
    WHERE id = ?
    """, (json.dumps(extracted_metrics), document_id))
    conn.commit()
    conn.close()

    return extracted_metrics
