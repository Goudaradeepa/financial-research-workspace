import re
from pathlib import Path
from typing import Optional, Dict, Any
import pymupdf

KNOWN_COMPANIES = {
    "cognizant": "Cognizant",
    "ctsh": "Cognizant",
    "cognizant technology solutions": "Cognizant",
    "tcs": "Tata Consultancy Services",
    "tata consultancy services": "Tata Consultancy Services",
    "infosys": "Infosys",
    "infy": "Infosys",
    "wipro": "Wipro",
    "hcl": "HCL Technologies",
    "hcltech": "HCL Technologies",
    "hcl technologies": "HCL Technologies",
    "tech mahindra": "Tech Mahindra",
    "ltimindtree": "LTIMindtree",
    "apple": "Apple Inc.",
    "aapl": "Apple Inc.",
    "microsoft": "Microsoft Corporation",
    "msft": "Microsoft Corporation",
    "tesla": "Tesla, Inc.",
    "tsla": "Tesla, Inc.",
    "nvidia": "NVIDIA Corporation",
    "nvda": "NVIDIA Corporation",
    "amazon": "Amazon.com, Inc.",
    "amzn": "Amazon.com, Inc.",
    "google": "Alphabet Inc.",
    "alphabet": "Alphabet Inc.",
    "goog": "Alphabet Inc.",
    "meta": "Meta Platforms, Inc.",
    "facebook": "Meta Platforms, Inc.",
    "netflix": "Netflix, Inc.",
    "nflx": "Netflix, Inc.",
    "accenture": "Accenture",
    "ibm": "IBM Corporation",
    "reliance": "Reliance Industries",
    "hdfc": "HDFC Bank",
    "icici": "ICICI Bank"
}

NOISE_WORDS = [
    r"\bintegrated\s+annual\s+report\b",
    r"\bannual\s+report\b",
    r"\bform\s+10-?k\b",
    r"\bform\s+10-?q\b",
    r"\bform\s+8-?k\b",
    r"\b10-?k\b",
    r"\b10-?q\b",
    r"\b8-?k\b",
    r"\bearnings\s+call\s+transcript\b",
    r"\bearnings\s+transcript\b",
    r"\bearnings\b",
    r"\btranscript\b",
    r"\breport\b",
    r"\bfinancial\s+statements?\b",
    r"\bfinancial\s+results?\b",
    r"\bpresentation\b",
    r"\bfy\s*20\d\d\b",
    r"\bfy\s*\d\d\b",
    r"\b20\d\d\s*[-–—]\s*\d\d\b",
    r"\b20\d\d\b",
    r"\bq[1-4]\b",
    r"\b2pager\b",
    r"\bpdf\b"
]

def clean_company_candidate(text: str) -> Optional[str]:
    """Cleans up a candidate company string."""
    if not text:
        return None
    cleaned = text.strip(" _-–—\t\r\n.,:;()[]{}")
    if len(cleaned) < 2 or len(cleaned) > 80:
        return None
    # Avoid generic words
    lower = cleaned.lower()
    if lower in ["annual report", "financial report", "form 10-k", "document", "united states", "securities and exchange commission"]:
        return None
    return cleaned

def identify_company_from_filename(filename: str) -> Optional[str]:
    """Identifies company name from the filename using known aliases or pattern extraction."""
    stem = Path(filename).stem
    stem_lower = stem.lower()

    # 1. Check known company keywords in filename
    for keyword, canonical in KNOWN_COMPANIES.items():
        # Match whole word boundary
        if re.search(r"(?:^|[\s_\-\.,])" + re.escape(keyword) + r"(?:$|[\s_\-\.,])", stem_lower):
            return canonical

    # 2. Strip financial noise phrases from stem
    clean_stem = stem
    for noise in NOISE_WORDS:
        clean_stem = re.sub(noise, " ", clean_stem, flags=re.IGNORECASE)

    clean_stem = re.sub(r"[\s_\-\.,]+", " ", clean_stem).strip()
    candidate = clean_company_candidate(clean_stem)
    if candidate and len(candidate.split()) <= 4:
        # Title case if all lowercase
        if candidate.islower():
            return candidate.title()
        return candidate

    return None

def identify_company_from_pdf_content(file_path: Path) -> Optional[str]:
    """
    Parses first few pages of a PDF to identify the issuing company.
    Checks SEC filing headers, corporate entity names, and known aliases.
    """
    if not file_path.exists():
        return None

    try:
        doc = pymupdf.open(str(file_path))
        num_pages_to_check = min(3, len(doc))
        first_pages_text = []

        for p_idx in range(num_pages_to_check):
            page_text = doc[p_idx].get_text("text") or ""
            first_pages_text.append(page_text)

        doc.close()
        combined_text = "\n".join(first_pages_text)
        combined_lower = combined_text.lower()

        # 1. Check known companies in first pages text
        for keyword, canonical in KNOWN_COMPANIES.items():
            if re.search(r"\b" + re.escape(keyword) + r"\b", combined_lower):
                return canonical

        # 2. Check standard SEC Form 10-K header pattern
        # "COMPANY NAME"
        # (Exact name of Registrant as specified in its charter)
        sec_pattern = r"(?:^|\n)\s*([A-Z0-9\s&.,'-]{3,60})\s*\n\s*\((?:exact\s+name\s+of\s+registrant|exact\s+name\s+of\s+company)"
        match = re.search(sec_pattern, combined_text, re.IGNORECASE)
        if match:
            candidate = clean_company_candidate(match.group(1))
            if candidate:
                return candidate.title() if candidate.isupper() else candidate

        sec_pattern_rev = r"\((?:exact\s+name\s+of\s+registrant|exact\s+name\s+of\s+company)[^\)]*\)\s*\n\s*([A-Z0-9\s&.,'-]{3,60})"
        match_rev = re.search(sec_pattern_rev, combined_text, re.IGNORECASE)
        if match_rev:
            candidate = clean_company_candidate(match_rev.group(1))
            if candidate:
                return candidate.title() if candidate.isupper() else candidate

        # 3. Look for Corporate Suffixes (Limited, Ltd, Inc, Corp, Corporation, LLC, Plc)
        corp_pattern = r"\b([A-Z][A-Za-z0-9&.,'-]+(?:\s+[A-Z][A-Za-z0-9&.,'-]+){0,4}\s+(?:Limited|Ltd\.?|Inc\.?|Incorporated|Corp\.?|Corporation|Plc|P\.L\.C\.))\b"
        matches = re.findall(corp_pattern, combined_text)
        for m in matches:
            cand = clean_company_candidate(m)
            if cand and not any(skip in cand.lower() for skip in ["securities and exchange commission", "united states", "annual report"]):
                return cand

    except Exception as e:
        print(f"[CompanyDetector] Error reading PDF {file_path}: {e}")

    return None

def detect_company_name(
    filename: str, 
    file_path: Optional[Path] = None, 
    user_hint: Optional[str] = None
) -> Optional[str]:
    """
    Main entry point for company identification.
    Strictly independent of Research Session name and session ticker.
    1. If user explicitly entered a company name, use it.
    2. Try to identify from filename (e.g. 'cognizant annual report.pdf' -> 'Cognizant').
    3. Try to identify from PDF content / cover page / SEC header.
    4. Never fallback to session name/ticker. Return None if not identified.
    """
    if user_hint and user_hint.strip():
        return user_hint.strip()

    # Step 1: Detect from filename
    from_filename = identify_company_from_filename(filename)
    if from_filename:
        return from_filename

    # Step 2: Detect from PDF content
    if file_path and file_path.exists() and file_path.suffix.lower() == ".pdf":
        from_content = identify_company_from_pdf_content(file_path)
        if from_content:
            return from_content

    return None
