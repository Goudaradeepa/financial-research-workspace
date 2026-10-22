import re
from typing import Dict, Any, List, Optional

class DocumentRelevanceClassification:
    FINANCIAL = "FINANCIAL"
    NON_FINANCIAL = "NON_FINANCIAL"
    UNCERTAIN = "UNCERTAIN"

# Thematic Indicator Groups
FILING_AND_STATEMENT_INDICATORS = [
    r"\bannual\s+report\b",
    r"\bintegrated\s+annual\s+report\b",
    r"\bform\s+10-k\b",
    r"\b10-k\b",
    r"\bform\s+10-q\b",
    r"\b10-q\b",
    r"\bform\s+8-k\b",
    r"\bquarterly\s+report\b",
    r"\bfinancial\s+statements?\b",
    r"\bconsolidated\s+financial\s+statements?\b",
    r"\bconsolidated\s+statements?\b",
    r"\bbalance\s+sheets?\b",
    r"\bconsolidated\s+balance\s+sheets?\b",
    r"\bincome\s+statements?\b",
    r"\bstatements?\s+of\s+operations?\b",
    r"\bstatements?\s+of\s+profit\s+and\s+loss\b",
    r"\bstatements?\s+of\s+cash\s+flows?\b",
    r"\bcash\s+flow\s+statements?\b",
    r"\bstatements?\s+of\s+financial\s+position\b",
    r"\bauditor'?s?\s+report\b",
    r"\bindependent\s+auditor'?s?\s+report\b",
    r"\bmanagement'?s?\s+discussion\s+and\s+analysis\b",
    r"\bnotes\s+to\s+consolidated\s+financial\s+statements\b",
    r"\bnotes\s+to\s+financial\s+statements\b",
]

CORE_METRIC_INDICATORS = [
    r"\brevenues?\b",
    r"\btotal\s+revenues?\b",
    r"\bnet\s+sales\b",
    r"\bnet\s+income\b",
    r"\bnet\s+profit\b",
    r"\bprofit\s+after\s+tax\b",
    r"\boperating\s+income\b",
    r"\boperating\s+profit\b",
    r"\boperating\s+margins?\b",
    r"\bgross\s+profit\b",
    r"\bgross\s+margins?\b",
    r"\bebitda\b",
    r"\bebit\b",
    r"\bdiluted\s+eps\b",
    r"\bearnings\s+per\s+share\b",
    r"\btotal\s+assets\b",
    r"\bcurrent\s+assets\b",
    r"\btotal\s+liabilities\b",
    r"\bcurrent\s+liabilities\b",
    r"\bstockholders'?\s+equity\b",
    r"\bshareholders'?\s+equity\b",
    r"\bshareholders'?\s+funds\b",
    r"\btotal\s+debt\b",
    r"\blong-term\s+debt\b",
    r"\boperating\s+cash\s+flow\b",
    r"\bfree\s+cash\s+flow\b",
    r"\bfiscal\s+year\b",
    r"\bfinancial\s+results?\b",
    r"\bcompany\s+financial\s+performance\b",
]

NON_FINANCIAL_INDICATORS = [
    # Academic & Examination
    r"\bquestion\s+paper\b",
    r"\bexamination\b",
    r"\bsemester\b",
    r"\bsyllabus\b",
    r"\broll\s+no\b",
    r"\breg\s+no\b",
    r"\bcourse\s+code\b",
    r"\bmaximum\s+marks\b",
    r"\bassignment\b",
    r"\bhomework\b",
    r"\blecture\s+notes\b",
    r"\bfaculty\s+of\b",
    r"\bdepartment\s+of\b",
    # Technical & Programming
    r"\bpython\s+(?:programming|tutorial|notes|code)\b",
    r"\bjava\s+(?:programming|tutorial|notes|code)\b",
    r"\bprogramming\s+in\s+\w+\b",
    r"\bdata\s+structures\b",
    r"\balgorithms?\b",
    r"\bbinary\s+tree\b",
    r"\bleetcode\b",
    r"\bclass\s+\w+\s*\{",
    r"\bdef\s+\w+\s*\(",
    # Resumes & Portfolios
    r"\bcurriculum\s+vitae\b",
    r"\bresume\b",
    r"\bcareer\s+objective\b",
    r"\btechnical\s+skills\b",
    r"\bwork\s+experience\b",
    # Manuals & Certificates
    r"\buser\s+manual\b",
    r"\binstallation\s+guide\b",
    r"\bcertificate\s+of\s+completion\b",
    r"\bcertificate\s+of\s+achievement\b",
]

def validate_document_relevance(
    document_name: str,
    extracted_text: str,
    ext: Optional[str] = None
) -> Dict[str, Any]:
    """
    Lightweight document relevance validation gate.
    Classifies an uploaded document into:
      1. FINANCIAL
      2. NON_FINANCIAL
      3. UNCERTAIN
      
    Returns a dict with classification, confidence, and human-readable reason.
    """
    name_clean = document_name.lower()
    text_clean = (extracted_text or "").lower()
    total_words = len(text_clean.split())
    combined_sample = f"{name_clean}\n{text_clean[:25000]}"

    # Check for Non-Financial markers
    matched_non_financial = [
        p for p in NON_FINANCIAL_INDICATORS if re.search(p, combined_sample, re.IGNORECASE)
    ]

    # Check for Filing & Statement markers
    matched_filings = [
        p for p in FILING_AND_STATEMENT_INDICATORS if re.search(p, combined_sample, re.IGNORECASE)
    ]

    # Check for Core Financial Metrics
    matched_metrics = [
        p for p in CORE_METRIC_INDICATORS if re.search(p, combined_sample, re.IGNORECASE)
    ]

    total_financial_matches = len(matched_filings) + len(matched_metrics)

    # 1. Clear Non-Financial Indicators (academic, resume, programming, syllabus, etc.)
    if len(matched_non_financial) >= 1 and len(matched_filings) == 0:
        return {
            "classification": DocumentRelevanceClassification.NON_FINANCIAL,
            "confidence": "HIGH",
            "reason": "This document appears to be a technical/academic document and does not contain sufficient financial-report content.",
            "matched_filings": len(matched_filings),
            "matched_metrics": len(matched_metrics),
            "matched_non_financial": len(matched_non_financial)
        }

    # 2. Clear Financial Indicators (e.g. Form 10-K, annual report, balance sheets + revenue/profit metrics)
    if (len(matched_filings) >= 1 and len(matched_metrics) >= 1) or total_financial_matches >= 4:
        return {
            "classification": DocumentRelevanceClassification.FINANCIAL,
            "confidence": "HIGH",
            "reason": "Financial document detected because the document contains annual-report and financial-statement terminology including revenue, net income, assets and liabilities.",
            "matched_filings": len(matched_filings),
            "matched_metrics": len(matched_metrics),
            "matched_non_financial": len(matched_non_financial)
        }

    # 3. Non-financial due to lack of any financial indicators in substantial content
    if total_words >= 35 and total_financial_matches == 0:
        return {
            "classification": DocumentRelevanceClassification.NON_FINANCIAL,
            "confidence": "HIGH",
            "reason": "This document does not contain sufficient financial-report content.",
            "matched_filings": len(matched_filings),
            "matched_metrics": len(matched_metrics),
            "matched_non_financial": len(matched_non_financial)
        }

    # 4. Ambiguous / UNCERTAIN cases:
    # - Insufficient text (< 35 words)
    # - 1 or 2 isolated financial words with no filing structure and no non-financial keywords
    return {
        "classification": DocumentRelevanceClassification.UNCERTAIN,
        "confidence": "LOW",
        "reason": "Unable to confidently determine whether this document is a financial report.",
        "matched_filings": len(matched_filings),
        "matched_metrics": len(matched_metrics),
        "matched_non_financial": len(matched_non_financial)
    }
