import os
import json
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, List

from database import get_db_connection

def classify_financial_doc(filename: str, text: str, ext: str) -> str:
    name_lower = filename.lower()
    text_lower = text[:5000].lower() if text else ""

    if "10-k" in name_lower or "10k" in name_lower or "form 10-k" in text_lower or "annual report" in text_lower:
        return "Form 10-K (Annual Report)"
    if "10-q" in name_lower or "10q" in name_lower or "form 10-q" in text_lower or "quarterly report" in text_lower:
        return "Form 10-Q (Quarterly Report)"
    if "8-k" in name_lower or "8k" in name_lower or "form 8-k" in text_lower or "current report" in text_lower:
        return "Form 8-K (Current Report)"
    if any(k in name_lower for k in ["transcript", "call", "earnings"]) or any(k in text_lower for k in ["conference call", "earnings call", "operator:", "questions and answers", "q&a session"]):
        return "Earnings Call Transcript"
    if "balance sheet" in name_lower or "balance sheet" in text_lower or "consolidated balance sheets" in text_lower:
        return "Financial Statement (Balance Sheet)"
    if "cash flow" in name_lower or "cash flows" in text_lower or "operating activities" in text_lower:
        return "Financial Statement (Cash Flows)"
    if any(k in name_lower for k in ["income", "operations", "p&l"]) or any(k in text_lower for k in ["statement of operations", "income statement", "revenues"]):
        return "Financial Statement (Income Statement)"
    if ext in [".csv", ".xlsx", ".xls"]:
        return "Financial Dataset / Metrics"
    if "presentation" in name_lower or "investor" in name_lower:
        return "Investor Presentation"
    if "press" in name_lower or "release" in name_lower or "news" in name_lower:
        return "Press Release"
    
    return "Financial Research Document"

def extract_financial_metrics(text: str) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {
        "detected_periods": [],
        "currencies": [],
        "key_indicators_found": []
    }
    if not text:
        return metrics

    sample = text[:20000]

    periods = set(re.findall(r"\b(?:FY\s*20\d\d|Q[1-4]\s*20\d\d|20\d\d|Three\s+Months\s+Ended|Twelve\s+Months\s+Ended)\b", sample, re.IGNORECASE))
    metrics["detected_periods"] = list(periods)[:5]

    currencies = set()
    if "$" in sample or "USD" in sample:
        currencies.add("USD ($)")
    if "EUR" in sample or "€" in sample:
        currencies.add("EUR (€)")
    if "GBP" in sample or "£" in sample:
        currencies.add("GBP (£)")
    metrics["currencies"] = list(currencies)

    indicators = [
        "Revenue", "Net Income", "Operating Income", "Gross Margin", 
        "EBITDA", "Diluted EPS", "Free Cash Flow", "Total Assets",
        "Total Liabilities", "Stockholders' Equity", "R&D Expense"
    ]
    found_indicators = [ind for ind in indicators if re.search(r"\b" + re.escape(ind) + r"\b", sample, re.IGNORECASE)]
    metrics["key_indicators_found"] = found_indicators

    return metrics

def chunk_text(text: str, chunk_size_words: int = 400) -> List[Dict[str, Any]]:
    if not text:
        return []
    
    words = text.split()
    chunks = []
    chunk_index = 0

    for i in range(0, len(words), chunk_size_words):
        chunk_words = words[i:i + chunk_size_words]
        content = " ".join(chunk_words)
        token_estimate = int(len(chunk_words) * 1.3)
        chunks.append({
            "chunk_index": chunk_index,
            "content": content,
            "token_estimate": token_estimate,
            "word_count": len(chunk_words)
        })
        chunk_index += 1

    return chunks

def process_document(document_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM financial_documents WHERE id = ?", (document_id,))
        doc = cursor.fetchone()
        if not doc:
            print(f"Document {document_id} not found in database.")
            conn.close()
            return

        now = datetime.utcnow().isoformat()
        cursor.execute("UPDATE financial_documents SET processing_status = 'PROCESSING', updated_at = ? WHERE id = ?", (now, document_id))
        conn.commit()

        file_path = Path(doc["file_path"])
        if not file_path.exists():
            raise FileNotFoundError(f"Storage file not found at {file_path}")

        ext = file_path.suffix.lower()
        extracted_text = ""
        page_count = 1

        if ext == ".pdf":
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                page_count = len(reader.pages)
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    pages_text.append(f"--- [Page {idx + 1}] ---\n" + page_text)
                extracted_text = "\n\n".join(pages_text)

        elif ext == ".csv":
            import pandas as pd
            df = pd.read_csv(file_path, nrows=500)
            page_count = 1
            row_count, col_count = df.shape
            summary_info = f"CSV Dataset: {row_count} rows, {col_count} columns.\nColumns: {', '.join(df.columns.astype(str))}\n\nData Preview (First 15 rows):\n"
            try:
                summary_info += df.head(15).to_markdown(index=False)
            except Exception:
                summary_info += df.head(15).to_string(index=False)
            extracted_text = summary_info

        elif ext in [".xlsx", ".xls"]:
            import pandas as pd
            excel_file = pd.ExcelFile(file_path)
            sheets_text = []
            page_count = len(excel_file.sheet_names)
            for sheet in excel_file.sheet_names[:5]:
                df = pd.read_excel(excel_file, sheet_name=sheet, nrows=100)
                sheets_text.append(f"--- [Sheet: {sheet}] ({df.shape[0]} rows, {df.shape[1]} cols) ---\n" + df.head(10).to_string(index=False))
            extracted_text = "\n\n".join(sheets_text)

        elif ext in [".txt", ".md"]:
            try:
                extracted_text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                extracted_text = file_path.read_text(encoding="latin-1", errors="replace")
            page_count = max(1, len(extracted_text) // 3000)

        elif ext == ".json":
            try:
                raw = file_path.read_text(encoding="utf-8")
                parsed = json.loads(raw)
                extracted_text = json.dumps(parsed, indent=2)
            except Exception:
                extracted_text = file_path.read_text(encoding="latin-1", errors="replace")
            page_count = 1

        else:
            try:
                extracted_text = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                extracted_text = f"[Binary preview not available for format {ext}]"

        word_count = len(extracted_text.split()) if extracted_text else 0
        doc_type = classify_financial_doc(doc["document_name"], extracted_text, ext)
        financial_metrics = extract_financial_metrics(extracted_text)
        
        clean_preview = re.sub(r"\s+", " ", extracted_text[:400]).strip()
        summary_snippet = clean_preview if clean_preview else f"{doc_type} with {page_count} pages."

        chunks = chunk_text(extracted_text, chunk_size_words=400)

        cursor.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chk_{idx}"
            cursor.execute("""
            INSERT INTO document_chunks (id, document_id, session_id, chunk_index, content, token_estimate, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk_id,
                document_id,
                doc["session_id"],
                chunk["chunk_index"],
                chunk["content"],
                chunk["token_estimate"],
                json.dumps({"word_count": chunk["word_count"]})
            ))

        now_ready = datetime.utcnow().isoformat()
        cursor.execute("""
        UPDATE financial_documents 
        SET processing_status = 'READY',
            error_message = NULL,
            document_type = ?,
            page_count = ?,
            word_count = ?,
            summary_snippet = ?,
            extracted_text = ?,
            financial_metrics = ?,
            updated_at = ?
        WHERE id = ?
        """, (
            doc_type,
            page_count,
            word_count,
            summary_snippet,
            extracted_text,
            json.dumps(financial_metrics),
            now_ready,
            document_id
        ))
        conn.commit()
        print(f"Successfully processed document: {doc['document_name']} ({doc_type}, {word_count} words)")

    except Exception as e:
        err_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Failed to process document {document_id}: {err_msg}")
        now_err = datetime.utcnow().isoformat()
        cursor.execute("""
        UPDATE financial_documents 
        SET processing_status = 'FAILED',
            error_message = ?,
            updated_at = ?
        WHERE id = ?
        """, (str(e), now_err, document_id))
        conn.commit()

    finally:
        conn.close()
