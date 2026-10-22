import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
DB_PATH = STORAGE_DIR / "workspace.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS research_sessions (
        id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        ticker VARCHAR(20),
        tags TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS financial_documents (
        id VARCHAR(36) PRIMARY KEY,
        session_id VARCHAR(36) NOT NULL,
        company_name VARCHAR(255),
        document_name VARCHAR(255) NOT NULL,
        document_type VARCHAR(100) NOT NULL,
        file_path TEXT NOT NULL,
        upload_date TEXT NOT NULL,
        processing_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
        file_size_bytes INTEGER DEFAULT 0,
        page_count INTEGER DEFAULT 0,
        word_count INTEGER DEFAULT 0,
        summary_snippet TEXT,
        extracted_text TEXT,
        financial_metrics TEXT,
        relevance_status VARCHAR(50) DEFAULT 'FINANCIAL',
        relevance_reason TEXT,
        error_message TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        CONSTRAINT fk_document_session FOREIGN KEY (session_id) REFERENCES research_sessions(id) ON DELETE CASCADE,
        CONSTRAINT chk_processing_status CHECK (processing_status IN ('PENDING', 'PROCESSING', 'PARSING', 'CHUNKING', 'EMBEDDING', 'INDEXING', 'READY', 'COMPLETED', 'FAILED'))
    );
    """)

    # Migration check for existing SQLite databases
    cursor.execute("PRAGMA table_info(financial_documents)")
    doc_cols = [row[1] for row in cursor.fetchall()]
    if "relevance_status" not in doc_cols:
        cursor.execute("ALTER TABLE financial_documents ADD COLUMN relevance_status VARCHAR(50) DEFAULT 'FINANCIAL';")
    if "relevance_reason" not in doc_cols:
        cursor.execute("ALTER TABLE financial_documents ADD COLUMN relevance_reason TEXT;")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id VARCHAR(64) PRIMARY KEY,
        document_id VARCHAR(36) NOT NULL,
        session_id VARCHAR(36) NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        token_estimate INTEGER DEFAULT 0,
        metadata TEXT,
        CONSTRAINT fk_chunk_document FOREIGN KEY (document_id) REFERENCES financial_documents(id) ON DELETE CASCADE,
        CONSTRAINT fk_chunk_session FOREIGN KEY (session_id) REFERENCES research_sessions(id) ON DELETE CASCADE
    );
    """)

    # 4. Multi-Agent Orchestration Audit Trail
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_runs (
        id VARCHAR(36) PRIMARY KEY,
        session_id VARCHAR(36) NOT NULL,
        document_id VARCHAR(36) NOT NULL,
        agent_name VARCHAR(50) NOT NULL,
        status VARCHAR(30) NOT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        output_summary TEXT,
        error_message TEXT,
        CONSTRAINT fk_run_session FOREIGN KEY (session_id) REFERENCES research_sessions(id) ON DELETE CASCADE,
        CONSTRAINT fk_run_document FOREIGN KEY (document_id) REFERENCES financial_documents(id) ON DELETE CASCADE
    );
    """)

    # 5. Red Flag Agent Findings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS red_flags (
        id VARCHAR(36) PRIMARY KEY,
        session_id VARCHAR(36) NOT NULL,
        document_id VARCHAR(36) NOT NULL,
        company_name VARCHAR(255),
        flag_type VARCHAR(100) NOT NULL,
        title VARCHAR(255) NOT NULL,
        description TEXT NOT NULL,
        supporting_metrics TEXT,
        fiscal_period VARCHAR(50),
        severity VARCHAR(20) DEFAULT 'MEDIUM',
        source_page INTEGER,
        source_chunk_id VARCHAR(64),
        evidence_text TEXT,
        explanation TEXT NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'FLAGGED',
        created_at TEXT NOT NULL,
        CONSTRAINT fk_flag_session FOREIGN KEY (session_id) REFERENCES research_sessions(id) ON DELETE CASCADE,
        CONSTRAINT fk_flag_document FOREIGN KEY (document_id) REFERENCES financial_documents(id) ON DELETE CASCADE
    );
    """)

    # 6. Conversational Research Queries
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS research_queries (
        id VARCHAR(36) PRIMARY KEY,
        session_id VARCHAR(36) NOT NULL,
        query_text TEXT NOT NULL,
        answer_text TEXT NOT NULL,
        agent_used VARCHAR(50) NOT NULL,
        sources TEXT,
        created_at TEXT NOT NULL,
        CONSTRAINT fk_query_session FOREIGN KEY (session_id) REFERENCES research_sessions(id) ON DELETE CASCADE
    );
    """)

    # 7. Report Agent Generated Reports
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS generated_reports (
        id VARCHAR(36) PRIMARY KEY,
        session_id VARCHAR(36) NOT NULL,
        document_id VARCHAR(36) NOT NULL,
        company_name VARCHAR(255),
        title VARCHAR(255) NOT NULL,
        executive_summary TEXT NOT NULL,
        key_financials TEXT NOT NULL,
        sources TEXT NOT NULL,
        created_at TEXT NOT NULL,
        CONSTRAINT fk_report_session FOREIGN KEY (session_id) REFERENCES research_sessions(id) ON DELETE CASCADE,
        CONSTRAINT fk_report_document FOREIGN KEY (document_id) REFERENCES financial_documents(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_session_id ON financial_documents(session_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_company_name ON financial_documents(company_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_processing_status ON financial_documents(processing_status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_document_type ON financial_documents(document_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON research_sessions(updated_at DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_chunk ON document_chunks(document_id, chunk_index);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_doc ON agent_runs(document_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_red_flags_doc ON red_flags(document_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_research_queries_session ON research_queries(session_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_generated_reports_doc ON generated_reports(document_id);")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database schema initialized successfully at {DB_PATH}")
