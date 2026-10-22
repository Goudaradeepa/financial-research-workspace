import os
import re
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

import pymupdf  # PyMuPDF
import faiss
from fastembed import TextEmbedding

from database import get_db_connection, STORAGE_DIR

VECTOR_DIR = STORAGE_DIR / "vector_indices"
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

# Shared embedding model singleton
_embedding_model: Optional[TextEmbedding] = None

def get_embedding_model() -> TextEmbedding:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embedding_model

def clean_text(text: str) -> str:
    """
    Cleans extracted text by normalizing whitespace, removing repetitive 
    page/header artifacts, and fixing hyphenated line breaks.
    """
    if not text:
        return ""
    
    # Normalize unicode
    text = text.replace("\xa0", " ").replace("\u2013", "-").replace("\u2014", "-")
    
    # Fix hyphenated words at line breaks (e.g. "com-\npany" -> "company")
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
    
    # Replace multiple newlines with double newline (paragraph preservation)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Replace single line breaks inside sentences with a space
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Remove standalone page numbers like "Page 12" or "12"
        if re.match(r"^(?:page\s*)?\d+\s*$", stripped, re.IGNORECASE):
            continue
        if stripped:
            cleaned_lines.append(stripped)
            
    return "\n".join(cleaned_lines)

def extract_pdf_pages_pymupdf(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extracts text from a PDF file using PyMuPDF while strictly preserving page numbers.
    Returns list of {"page_number": int, "text": str}.
    """
    doc = pymupdf.open(str(file_path))
    pages = []
    
    for page_index in range(len(doc)):
        page = doc[page_index]
        raw_text = page.get_text("text") or ""
        cleaned = clean_text(raw_text)
        pages.append({
            "page_number": page_index + 1,
            "text": cleaned if cleaned else raw_text.strip()
        })
        
    doc.close()
    return pages

def chunk_pages_with_provenance(
    pages: List[Dict[str, Any]], 
    doc_id: str, 
    session_id: str, 
    target_words: int = 350
) -> List[Dict[str, Any]]:
    """
    Divides page text into reasonable chunks while recording document ID, 
    chunk ID, page number, and source text for full provenance tracing.
    """
    chunks = []
    chunk_counter = 0

    for page_info in pages:
        page_num = page_info["page_number"]
        page_text = page_info["text"]
        if not page_text:
            continue

        words = page_text.split()
        if len(words) <= target_words:
            chunk_id = f"{doc_id}_p{page_num}_c{chunk_counter}"
            chunks.append({
                "id": chunk_id,
                "document_id": doc_id,
                "session_id": session_id,
                "chunk_index": chunk_counter,
                "page_number": page_num,
                "content": page_text,
                "token_estimate": int(len(words) * 1.3),
                "word_count": len(words)
            })
            chunk_counter += 1
        else:
            # Divide page into sub-chunks of target_words
            for i in range(0, len(words), target_words):
                chunk_words = words[i:i + target_words]
                sub_text = " ".join(chunk_words)
                chunk_id = f"{doc_id}_p{page_num}_c{chunk_counter}"
                chunks.append({
                    "id": chunk_id,
                    "document_id": doc_id,
                    "session_id": session_id,
                    "chunk_index": chunk_counter,
                    "page_number": page_num,
                    "content": sub_text,
                    "token_estimate": int(len(chunk_words) * 1.3),
                    "word_count": len(chunk_words)
                })
                chunk_counter += 1

    return chunks

def generate_embeddings_and_faiss_index(
    doc_id: str, 
    chunks: List[Dict[str, Any]]
) -> Tuple[str, int]:
    """
    Generates embeddings using sentence-transformers (all-MiniLM-L6-v2)
    and indexes them in FAISS (IndexFlatIP with L2 normalized vectors).
    Stores chunk provenance metadata mapping for retrieval.
    """
    if not chunks:
        # Create empty dummy index if document had no text
        index = faiss.IndexFlatIP(384)
        index_path = VECTOR_DIR / f"{doc_id}.faiss"
        faiss.write_index(index, str(index_path))
        return str(index_path), 0

    texts = [c["content"] for c in chunks]
    model = get_embedding_model()
    embeddings_generator = model.embed(texts)
    embeddings_list = list(embeddings_generator)
    
    embeddings = np.array(embeddings_list).astype("float32")
    faiss.normalize_L2(embeddings)
    
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # Save index to disk
    index_path = VECTOR_DIR / f"{doc_id}.faiss"
    faiss.write_index(index, str(index_path))

    # Save metadata mapping vector_idx -> chunk provenance
    meta_path = VECTOR_DIR / f"{doc_id}_meta.json"
    provenance_map = []
    for i, c in enumerate(chunks):
        provenance_map.append({
            "vector_idx": i,
            "chunk_id": c["id"],
            "document_id": c["document_id"],
            "session_id": c["session_id"],
            "page_number": c["page_number"],
            "token_estimate": c["token_estimate"],
            "content": c["content"]
        })

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(provenance_map, f, indent=2)

    return str(index_path), index.ntotal

def update_document_status(doc_id: str, status: str, error: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
    UPDATE financial_documents 
    SET processing_status = ?, error_message = ?, updated_at = ? 
    WHERE id = ?
    """, (status, error, now, doc_id))
    conn.commit()
    conn.close()

def run_document_agent_pipeline(document_id: str) -> Dict[str, Any]:
    """
    Executes the complete Document Agent pipeline:
    1. Parse PDF using PyMuPDF (preserving page numbers)
    2. Clean extracted text
    3. Divide into reasonable chunks with page provenance
    4. Generate sentence-transformer embeddings
    5. Index in FAISS with metadata tracking
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM financial_documents WHERE id = ?", (document_id,))
        doc = cursor.fetchone()
        if not doc:
            conn.close()
            raise ValueError(f"Document {document_id} not found in database")

        session_id = doc["session_id"]
        file_path = Path(doc["file_path"])
        if not file_path.exists():
            raise FileNotFoundError(f"Document file missing at {file_path}")

        # Step 1: Parsing
        update_document_status(document_id, "PARSING")
        ext = file_path.suffix.lower()
        pages = []

        if ext == ".pdf":
            pages = extract_pdf_pages_pymupdf(file_path)
        elif ext in [".txt", ".md"]:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            cleaned = clean_text(content)
            # Estimate 3000 chars per page
            page_slices = [cleaned[i:i+3000] for i in range(0, max(1, len(cleaned)), 3000)]
            for p_idx, p_text in enumerate(page_slices):
                pages.append({"page_number": p_idx + 1, "text": p_text})
        elif ext == ".csv":
            import pandas as pd
            df = pd.read_csv(file_path, nrows=300)
            text_repr = df.to_string(index=False)
            pages.append({"page_number": 1, "text": text_repr})
        else:
            raw = file_path.read_text(encoding="utf-8", errors="replace")
            pages.append({"page_number": 1, "text": clean_text(raw)})

        total_pages = len(pages)
        full_extracted_text = "\n\n".join([f"--- [Page {p['page_number']}] ---\n{p['text']}" for p in pages])
        word_count = len(full_extracted_text.split())

        # Step 2: Chunking with Page Provenance
        update_document_status(document_id, "CHUNKING")
        chunks = chunk_pages_with_provenance(pages, document_id, session_id, target_words=350)

        # Store chunks in SQLite
        cursor.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
        for c in chunks:
            chunk_meta = {
                "page_number": c["page_number"],
                "word_count": c["word_count"]
            }
            cursor.execute("""
            INSERT INTO document_chunks (id, document_id, session_id, chunk_index, content, token_estimate, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                c["id"],
                document_id,
                session_id,
                c["chunk_index"],
                c["content"],
                c["token_estimate"],
                json.dumps(chunk_meta)
            ))
        conn.commit()

        # Step 3: Embedding Generation & FAISS Indexing
        update_document_status(document_id, "EMBEDDING")
        index_path, total_vectors = generate_embeddings_and_faiss_index(document_id, chunks)

        # Step 4: Finalize Document Readiness & Relevance Validation
        now = datetime.utcnow().isoformat()
        from processor import classify_financial_doc, extract_financial_metrics
        from company_detector import detect_company_name
        from document_validator import validate_document_relevance

        # Document Relevance Validation
        val_res = validate_document_relevance(doc["document_name"], full_extracted_text, ext)
        relevance_status = val_res["classification"]
        relevance_reason = val_res["reason"]

        if relevance_status == "NON_FINANCIAL":
            doc_type = "Non-Financial Document"
            metrics = []
        elif relevance_status == "UNCERTAIN":
            doc_type = "Document Type Uncertain"
            metrics = []
        else:
            doc_type = classify_financial_doc(doc["document_name"], full_extracted_text, ext)
            metrics = extract_financial_metrics(full_extracted_text)

        summary_snippet = full_extracted_text[:400].strip()

        # Independently detect company name if not already set
        company_name = doc["company_name"]
        if not company_name or company_name in ["Unassigned Company", "Detecting...", ""]:
            detected_company = detect_company_name(doc["document_name"], file_path)
            if detected_company:
                company_name = detected_company

        cursor.execute("""
        UPDATE financial_documents
        SET processing_status = 'READY',
            company_name = COALESCE(?, company_name),
            document_type = ?,
            relevance_status = ?,
            relevance_reason = ?,
            page_count = ?,
            word_count = ?,
            summary_snippet = ?,
            extracted_text = ?,
            financial_metrics = ?,
            error_message = NULL,
            updated_at = ?
        WHERE id = ?
        """, (
            company_name,
            doc_type,
            relevance_status,
            relevance_reason,
            total_pages,
            word_count,
            summary_snippet,
            full_extracted_text,
            json.dumps(metrics) if isinstance(metrics, (list, dict)) else "[]",
            now,
            document_id
        ))
        conn.commit()
        conn.close()

        print(f"[DocumentAgent] Document {document_id} indexed in FAISS ({total_vectors} vectors, {total_pages} pages). Relevance: {relevance_status}.")
        return {
            "document_id": document_id,
            "status": "READY",
            "page_count": total_pages,
            "chunk_count": len(chunks),
            "vector_count": total_vectors,
            "index_path": index_path,
            "relevance_status": relevance_status,
            "relevance_reason": relevance_reason
        }

    except Exception as e:
        err_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"[DocumentAgent] Error processing document {document_id}: {err_msg}")
        update_document_status(document_id, "FAILED", error=str(e))
        conn.close()
        raise
