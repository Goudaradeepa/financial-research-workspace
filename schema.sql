-- ============================================================================
-- Multi-Agent Financial Research System - Database Schema
-- Entities: Research Sessions & Financial Documents
-- ============================================================================

PRAGMA foreign_keys = ON;

-- 1. Research Sessions Table
CREATE TABLE IF NOT EXISTS research_sessions (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ticker VARCHAR(20),
    tags TEXT
);

-- 2. Financial Documents Table
CREATE TABLE IF NOT EXISTS financial_documents (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    company_name VARCHAR(255),
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    file_path TEXT NOT NULL,
    upload_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    
    file_size_bytes BIGINT DEFAULT 0,
    page_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    summary_snippet TEXT,
    extracted_text TEXT,
    financial_metrics TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_document_session
        FOREIGN KEY (session_id) 
        REFERENCES research_sessions(id) 
        ON DELETE CASCADE,

    CONSTRAINT chk_processing_status 
        CHECK (processing_status IN ('PENDING', 'PROCESSING', 'PARSING', 'CHUNKING', 'EMBEDDING', 'INDEXING', 'READY', 'COMPLETED', 'FAILED'))
);

-- 3. Document Chunks Table (Foundational for downstream Multi-Agent RAG retrieval)
CREATE TABLE IF NOT EXISTS document_chunks (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_estimate INTEGER DEFAULT 0,
    metadata TEXT,
    
    CONSTRAINT fk_chunk_document
        FOREIGN KEY (document_id) 
        REFERENCES financial_documents(id) 
        ON DELETE CASCADE,

    CONSTRAINT fk_chunk_session
        FOREIGN KEY (session_id) 
        REFERENCES research_sessions(id) 
        ON DELETE CASCADE
);

-- ============================================================================
-- Performance Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_documents_session_id 
    ON financial_documents(session_id);

CREATE INDEX IF NOT EXISTS idx_documents_company_name 
    ON financial_documents(company_name);

CREATE INDEX IF NOT EXISTS idx_documents_processing_status 
    ON financial_documents(processing_status);

CREATE INDEX IF NOT EXISTS idx_documents_document_type 
    ON financial_documents(document_type);

CREATE INDEX IF NOT EXISTS idx_sessions_updated_at 
    ON research_sessions(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_chunk 
    ON document_chunks(document_id, chunk_index);
