from pathlib import Path
import csv

SAMPLE_DIR = Path(__file__).resolve().parent

# 1. Earnings Call Transcript
transcript_text = """APPLE INC. Q3 2024 FINANCIAL RESULTS CONFERENCE CALL
Date: August 1, 2024
Participants:
- Tim Cook, Chief Executive Officer
- Luca Maestri, Chief Financial Officer
- Operator

Operator:
Good day and welcome to the Apple Inc. Third Quarter 2024 Financial Results Conference Call. Today's call is being recorded. At this time, for opening remarks and introductions, I would like to turn the call over to Suhasini Chandramouli, Director of Investor Relations.

Luca Maestri:
Thank you. Total revenue for the June quarter was $85.8 billion, up 5% year-over-year. We set a new June quarter revenue record in more than two dozen countries and regions, including Canada, Mexico, France, Germany, the UK, India, and Indonesia.
Products revenue was $61.6 billion, up 2% compared to last year, driven by the launch of our new iPad Air and iPad Pro powered by the M4 chip.
Services revenue reached a new all-time record of $24.2 billion, up 14% year-over-year.
Gross margin was 46.3%, near the high end of our guidance range. Operating expenses were $14.3 billion, well within our expectations. Net income was $21.4 billion and diluted earnings per share was $1.40, up 11% compared to a year ago.
Operating cash flow was very strong at $28.9 billion, and we returned over $32 billion to shareholders during the quarter.

Tim Cook:
Today, Apple is reporting a new June quarter revenue record of $85.8 billion, up 5% from a year ago. During the quarter, we were thrilled to announce incredible updates to our software platforms at our Worldwide Developers Conference, including Apple Intelligence, a personal intelligence system that puts powerful, private generative models at the core of iPhone, iPad, and Mac. We can't wait to share these tools with our users.

Operator:
We will now begin the Q&A session. First question comes from Shannon Cross with Credit Suisse.

Shannon Cross:
Thank you very much. Tim, could you talk more about how Apple Intelligence is expected to drive the iPhone upgrade cycle this fall?
"""

(SAMPLE_DIR / "Apple_Q3_2024_Earnings_Call_Transcript.txt").write_text(transcript_text, encoding="utf-8")

# 2. Form 10-K Annual Report Snippet
filing_text = """UNITED STATES SECURITIES AND EXCHANGE COMMISSION
Washington, D.C. 20549
FORM 10-K
(Mark One)
ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934
For the fiscal year ended September 30, 2024

MICROSOFT CORPORATION
Commission File Number 001-37845

PART I
Item 1. Business
Microsoft is a technology company whose mission is to empower every person and every organization on the planet to achieve more. We strive to create local opportunity, growth, and impact in every country around the world. Our platforms and tools help drive small business productivity, large business competitiveness, and public-sector efficiency.

Item 1A. Risk Factors
Our operations and financial results are subject to various risks and uncertainties, including:
- Intense competition across cloud computing, AI platforms, and personal computing.
- Rapid technological change, including generative AI models and data center infrastructure requirements.
- Significant capital investments in cloud infrastructure and specialized AI accelerators.
- Cybersecurity vulnerabilities and compliance with evolving international privacy regulations.

PART II
Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations
Total revenue was $245.1 billion for fiscal year 2024, compared to $211.9 billion in fiscal year 2023, an increase of 16%. Operating income was $109.4 billion, increasing 24%. Diluted EPS was $11.80, up 22%.
Microsoft Cloud revenue was $137.4 billion, up 23% year-over-year, driven by Azure expansion and AI services adoption.
Cash and cash equivalents totaled $34.7 billion as of September 30, 2024.
"""

(SAMPLE_DIR / "Microsoft_FY2024_Form_10K_Annual_Report.txt").write_text(filing_text, encoding="utf-8")

# 3. CSV Financial Metrics
csv_rows = [
    ["Metric", "FY2021", "FY2022", "FY2023", "FY2024", "YoY_Growth_Pct"],
    ["Total Revenue ($M)", "53823", "81462", "96773", "112340", "16.1%"],
    ["Automotive Sales ($M)", "47232", "71458", "82419", "93800", "13.8%"],
    ["Energy Generation & Storage ($M)", "2789", "3909", "6035", "9550", "58.2%"],
    ["Gross Profit ($M)", "13606", "20853", "17928", "19800", "10.4%"],
    ["Operating Income ($M)", "6523", "13656", "8891", "9450", "6.3%"],
    ["Net Income ($M)", "5519", "12583", "14997", "13200", "-12.0%"],
    ["Operating Margin (%)", "12.1%", "16.8%", "9.2%", "8.4%", "-80bps"],
    ["Free Cash Flow ($M)", "5015", "7566", "4358", "5200", "19.3%"],
    ["Cash & Investments ($M)", "17576", "22185", "29094", "33250", "14.3%"],
    ["Vehicle Deliveries (Units)", "936172", "1313851", "1808581", "1980000", "9.5%"],
]

with open(SAMPLE_DIR / "Tesla_Financial_Performance_and_Deliveries.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(csv_rows)

print("Sample financial files generated successfully in sample_docs/")
