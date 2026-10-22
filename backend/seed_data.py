import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import pymupdf

from database import get_db_connection, STORAGE_DIR
from document_agent import run_document_agent_pipeline
from extraction_agent import extract_all_financial_metrics
from orchestrator import run_full_document_pipeline

SEED_SESSION_ID = "seed-session-flagship-reports"

SEED_REPORTS = [
    {
        "filename": "Apple_Inc_FY2024_Form_10K.pdf",
        "company": "Apple Inc. (AAPL)",
        "ticker": "AAPL",
        "doc_type": "Form 10-K (Annual Report)",
        "pages": [
            """UNITED STATES SECURITIES AND EXCHANGE COMMISSION
WASHINGTON, D.C. 20549
FORM 10-K
ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934
For the fiscal year ended September 28, 2024

APPLE INC.
(Exact name of Registrant as specified in its charter)

PART I - ITEM 1. BUSINESS
Apple Inc. designs, manufactures and markets smartphones, personal computers, tablets, wearables and accessories, and sells a variety of related services.
The Company's fiscal year is the 52 or 53-week period that ends on the last Saturday of September. Fiscal year 2024 comprised 52 weeks.
The Company's products include iPhone, Mac, iPad, and Wearables, Home and Accessories. The Company's Services include Advertising, AppleCare, Cloud Services, Digital Content and Payment Services.
Apple Intelligence is deeply integrated into iOS 18, iPadOS 18 and macOS Sequoia, using generative models to transform personal computing.""",

            """PART II - ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS
CONSOLIDATED STATEMENTS OF OPERATIONS FOR FISCAL YEAR 2024

Total revenue was $391.0 billion in fiscal year 2024, compared to $383.3 billion in fiscal year 2023, representing an increase of 2%.
Services revenue was $96.2 billion, up 13% year-over-year. Products revenue was $294.8 billion.
Gross margin was 46.2% for fiscal year 2024, compared to 44.1% in fiscal year 2023.
Operating profit was $123.2 billion, compared to $114.3 billion in 2023. Operating margin was 31.5%.
EBITDA was $134.7 billion for fiscal year 2024.
Net profit was $93.7 billion, and diluted earnings per share EPS was $6.08, compared to $6.13 in 2023.
Free cash flow was $108.8 billion for the fiscal year ended September 28, 2024.""",

            """PART II - ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA
CONSOLIDATED BALANCE SHEETS AS OF SEPTEMBER 28, 2024 (in millions)

ASSETS
Cash and cash equivalents: $29,943
Marketable securities: $126,804
Inventories: $6,508
Total current assets: $152,987
Property, plant and equipment, net: $45,246
Total assets were $364.9 billion as of September 28, 2024.

LIABILITIES AND SHAREHOLDERS' EQUITY
Accounts payable: $65,373
Deferred revenue: $8,249
Commercial paper and current portion of long-term debt: $11,354
Total current liabilities: $160,254
Total debt was $106.6 billion, including long-term debt of $95.2 billion.
Total liabilities were $308.0 billion as of September 28, 2024.
Total shareholders' equity: $56,929 million."""
        ]
    },
    {
        "filename": "Microsoft_Corp_FY2024_Form_10K.pdf",
        "company": "Microsoft Corporation (MSFT)",
        "ticker": "MSFT",
        "doc_type": "Form 10-K (Annual Report)",
        "pages": [
            """UNITED STATES SECURITIES AND EXCHANGE COMMISSION
WASHINGTON, D.C. 20549
FORM 10-K
ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934
For the fiscal year ended June 30, 2024

MICROSOFT CORPORATION
(Exact name of Registrant as specified in its charter)

PART I - ITEM 1. BUSINESS
Microsoft is a technology provider committed to empowering every person and organization on the planet to achieve more.
We offer a wide range of cloud-based services, computing platforms, and developer tools.
Our segments are Productivity and Business Processes, Intelligent Cloud, and More Personal Computing.
Microsoft Cloud revenue exceeded $137 billion in fiscal year 2024, driven by Azure AI deployments and commercial Microsoft 365 expansion.""",

            """PART II - ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS
CONSOLIDATED RESULTS OF OPERATIONS FOR FISCAL YEAR 2024

Total revenue was $245.1 billion for fiscal year 2024, compared to $211.9 billion in fiscal year 2023, an increase of 16%.
Operating profit was $109.4 billion, increasing 24% from $88.5 billion in fiscal year 2023.
Operating margin was 44.6%, expanding 230 basis points.
EBITDA totaled $125.8 billion for fiscal year 2024.
Net profit was $88.1 billion, representing an increase of 22% year-over-year.
Diluted earnings per share EPS was $11.80, up 22% compared to $9.68 in fiscal year 2023.
Free cash flow generated was $74.1 billion, increasing 25%.""",

            """PART II - ITEM 8. FINANCIAL STATEMENTS
CONSOLIDATED BALANCE SHEETS AS OF JUNE 30, 2024

ASSETS
Cash, cash equivalents, and short-term investments: $75,548 million
Total current assets: $159,738 million
Property and equipment, net: $160,334 million
Total assets were $512.1 billion as of June 30, 2024.

LIABILITIES AND STOCKHOLDERS' EQUITY
Current liabilities: $118,655 million
Long-term debt and finance leases: $48,800 million
Total debt was $78.8 billion across all maturities.
Total liabilities were $243.6 billion as of June 30, 2024.
Total stockholders' equity was $268.5 billion."""
        ]
    },
    {
        "filename": "Tesla_Inc_FY2024_Form_10K.pdf",
        "company": "Tesla, Inc. (TSLA)",
        "ticker": "TSLA",
        "doc_type": "Form 10-K (Annual Report)",
        "pages": [
            """UNITED STATES SECURITIES AND EXCHANGE COMMISSION
WASHINGTON, D.C. 20549
FORM 10-K
ANNUAL REPORT FOR THE FISCAL YEAR ENDED DECEMBER 31, 2024

TESLA, INC.
(Exact name of Registrant as specified in its charter)

PART I - ITEM 1. BUSINESS
Tesla designs, develops, manufactures, sells and leases high-performance fully electric vehicles, energy generation and storage systems, and offers services related to its products.
Total vehicle deliveries in 2024 were 1.98 million units.
Energy storage deployments grew to 15.3 GWh in 2024, representing a 125% increase compared to 2023.
Tesla continues to deploy Full Self-Driving (FSD) Supervised neural network architectures globally.""",

            """PART II - ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS
CONSOLIDATED STATEMENTS OF OPERATIONS FOR FISCAL YEAR 2024

Total revenue was $112.3 billion for fiscal year 2024, compared to $96.8 billion in fiscal year 2023, an increase of 16.1%.
Automotive revenues were $93.8 billion. Energy generation and storage revenues were $9.55 billion.
Gross margin was 17.6% for fiscal year 2024.
Operating profit was $9.45 billion, resulting in an operating margin of 8.4%.
EBITDA was $14.8 billion for fiscal year 2024.
Net profit was $13.2 billion for the year. Diluted earnings per share EPS was $3.80.
Free cash flow was $5.2 billion, up 19% compared to 2023.""",

            """PART II - ITEM 8. CONSOLIDATED BALANCE SHEETS
AS OF DECEMBER 31, 2024 (in millions)

ASSETS
Cash, cash equivalents and investments: $33,250
Inventories: $14,250
Total current assets: $54,120
Property, plant and equipment, net: $35,680
Total assets were $115.5 billion as of December 31, 2024.

LIABILITIES AND EQUITY
Total liabilities were $46.8 billion as of December 31, 2024.
Total debt was $5.7 billion, consisting primarily of non-recourse financing and solar notes.
Total stockholders' equity: $68.7 billion."""
        ]
    },
    {
        "filename": "NVIDIA_Corp_FY2025_Form_10K.pdf",
        "company": "NVIDIA Corporation (NVDA)",
        "ticker": "NVDA",
        "doc_type": "Form 10-K (Annual Report)",
        "pages": [
            """UNITED STATES SECURITIES AND EXCHANGE COMMISSION
WASHINGTON, D.C. 20549
FORM 10-K
ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934
For the fiscal year ended January 26, 2025

NVIDIA CORPORATION
(Exact name of Registrant as specified in its charter)

PART I - ITEM 1. BUSINESS
NVIDIA pioneered accelerated computing to tackle challenges that ordinary computers cannot solve.
Our platforms address massive computing markets across Data Center, Gaming, Professional Visualization, and Automotive.
The Hopper architecture and Blackwell platform represent unprecedented compute density for generative AI training and real-time inference.""",

            """PART II - ITEM 7. RESULTS OF OPERATIONS
CONSOLIDATED STATEMENTS OF INCOME FOR FISCAL YEAR 2025

Total revenue was $130.5 billion for fiscal year 2025, up 114% compared to $60.9 billion in fiscal year 2024.
Data Center revenue was $115.2 billion, up 140% year-over-year.
Gross margin was 75.0% for fiscal year 2025, up from 72.7% in the prior year.
Operating profit was $78.2 billion, compared to $33.0 billion in fiscal year 2024.
Operating margin was 60.0% for fiscal year 2025.
EBITDA was $82.4 billion for fiscal year 2025.
Net profit was $65.8 billion, up 121% year-over-year. Diluted earnings per share EPS was $2.65.
Free cash flow reached $60.9 billion for fiscal year 2025.""",

            """PART II - ITEM 8. CONSOLIDATED BALANCE SHEETS
AS OF JANUARY 26, 2025 (in millions)

ASSETS
Cash, cash equivalents and marketable securities: $43,200
Total current assets: $68,500
Total assets were $98.4 billion as of January 26, 2025.

LIABILITIES AND SHAREHOLDERS' EQUITY
Total current liabilities: $15,800
Total debt was $8.5 billion across notes payable.
Total liabilities were $25.2 billion as of January 26, 2025.
Total shareholders' equity was $73.2 billion."""
        ]
    }
]

def generate_pdf(file_path: Path, pages_text: List[str]):
    """Generates a clean, valid multi-page PDF with PyMuPDF."""
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page(width=595, height=842) # A4
        # Margin: left 40, top 40, right 555, bottom 800
        rect = pymupdf.Rect(40, 40, 555, 800)
        page.insert_textbox(rect, text, fontsize=10, fontname="helv")
    doc.save(str(file_path))
    doc.close()

def seed_flagship_annual_reports() -> str:
    """
    Creates 4 realistic seed company annual report PDFs, inserts them into 
    the flagship research session, and runs each document through the EXACT 
    SAME Document Agent pipeline and Extraction Agent.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()
    session_dir = STORAGE_DIR / "sessions" / SEED_SESSION_ID
    session_dir.mkdir(parents=True, exist_ok=True)

    # 1. Ensure Seed Session exists
    cursor.execute("SELECT id FROM research_sessions WHERE id = ?", (SEED_SESSION_ID,))
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO research_sessions (id, name, description, created_at, updated_at, ticker, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            SEED_SESSION_ID,
            "Flagship Company Annual Reports (Pre-Indexed)",
            "Pre-loaded FY2024-2025 Form 10-K filings for Apple, Microsoft, Tesla, and NVIDIA, fully processed through the Document Agent & indexed in FAISS.",
            now,
            now,
            "MEGA-CAP",
            json.dumps(["MegaCap", "10-K", "Tech", "EV", "AI", "Pre-Indexed"])
        ))
        conn.commit()

    # 2. Process each Seed Report through the Document Agent Pipeline
    processed_count = 0
    for idx, report_cfg in enumerate(SEED_REPORTS):
        doc_id = f"seed-doc-{report_cfg['ticker'].lower()}-10k"
        target_path = session_dir / report_cfg["filename"]

        # Generate PDF on disk
        generate_pdf(target_path, report_cfg["pages"])
        file_size = target_path.stat().st_size

        cursor.execute("SELECT id FROM financial_documents WHERE id = ?", (doc_id,))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO financial_documents (
                id, session_id, company_name, document_name, document_type, file_path,
                upload_date, processing_status, file_size_bytes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?)
            """, (
                doc_id,
                SEED_SESSION_ID,
                report_cfg["company"],
                report_cfg["filename"],
                report_cfg["doc_type"],
                str(target_path),
                now,
                file_size,
                now,
                now
            ))
            conn.commit()

        # Run Full Multi-Agent Orchestrator Pipeline:
        # Document Agent -> Extraction Agent -> Red Flag Agent
        run_full_document_pipeline(doc_id)

        processed_count += 1
        print(f"[SeedData] Multi-Agent Pipeline completed for {report_cfg['filename']} (Document, Extraction & Red Flag Agents).")

    conn.close()
    return f"Successfully initialized {processed_count} seed company reports in session {SEED_SESSION_ID}."

if __name__ == "__main__":
    msg = seed_flagship_annual_reports()
    print(msg)
