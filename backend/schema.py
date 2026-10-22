"""
Database Schema Definition for Multi-Agent Financial Research System
Entities: ResearchSession & FinancialDocument
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

class ProcessingStatusEnum(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ResearchSessionEntity:
    """
    Represents a dedicated financial research workspace session.
    
    Fields:
      - id: Unique session identifier (UUID)
      - name: Research session title (e.g. 'Apple Q3 2024 Deep Dive')
      - description: Optional research goals, scope, and key questions
      - created_at: Timestamp of session creation
      - updated_at: Timestamp of latest session activity/update
      - ticker: Optional ticker symbol for target company (e.g. 'AAPL')
      - tags: Optional categorization tags
    """
    def __init__(
        self,
        id: str,
        name: str,
        description: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        ticker: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.ticker = ticker
        self.tags = tags or []

class FinancialDocumentEntity:
    """
    Represents a financial document uploaded to a research session.
    
    Fields:
      - id: Unique document identifier (UUID)
      - session_id: Foreign key linking document to a research session
      - company_name: Name of the company/issuer (e.g. 'Apple Inc.')
      - document_name: Original or designated filename (e.g. 'AAPL_10K_FY24.pdf')
      - document_type: Classification (e.g. 'Form 10-K', 'Earnings Call Transcript')
      - file_path: Persistent local storage path
      - upload_date: Timestamp of file upload
      - processing_status: Lifecycle status (PENDING, PROCESSING, READY, COMPLETED, FAILED)
    """
    def __init__(
        self,
        id: str,
        session_id: str,
        company_name: Optional[str],
        document_name: str,
        document_type: str,
        file_path: str,
        upload_date: Optional[datetime] = None,
        processing_status: ProcessingStatusEnum = ProcessingStatusEnum.PENDING,
        file_size_bytes: int = 0,
        page_count: int = 0,
        word_count: int = 0,
        summary_snippet: Optional[str] = None,
        extracted_text: Optional[str] = None,
        financial_metrics: Optional[dict] = None,
        error_message: Optional[str] = None
    ):
        self.id = id
        self.session_id = session_id
        self.company_name = company_name
        self.document_name = document_name
        self.document_type = document_type
        self.file_path = file_path
        self.upload_date = upload_date or datetime.utcnow()
        self.processing_status = processing_status
        self.file_size_bytes = file_size_bytes
        self.page_count = page_count
        self.word_count = word_count
        self.summary_snippet = summary_snippet
        self.extracted_text = extracted_text
        self.financial_metrics = financial_metrics or {}
        self.error_message = error_message
