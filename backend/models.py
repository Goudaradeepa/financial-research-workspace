from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PARSING = "PARSING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    READY = "READY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

# --- Research Session Models ---

class ResearchSessionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the research session")
    description: Optional[str] = Field(None, max_length=2000, description="Session description and goals")
    ticker: Optional[str] = Field(None, max_length=20, description="Optional target company ticker symbol")
    tags: Optional[List[str]] = Field(default_factory=list, description="Optional categorization tags")

SessionCreate = ResearchSessionCreate

class ResearchSessionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    ticker: Optional[str] = None
    tags: Optional[List[str]] = None

SessionUpdate = ResearchSessionUpdate

class ResearchSessionResponse(BaseModel):
    id: str = Field(..., description="Unique research session identifier")
    name: str = Field(..., description="Name of the research session")
    description: Optional[str] = Field(None, description="Description of research session")
    created_at: str = Field(..., description="Timestamp when session was created")
    updated_at: str = Field(..., description="Timestamp when session was last updated")
    ticker: Optional[str] = None
    tags: List[str] = []
    document_count: int = 0
    total_size_bytes: int = 0

SessionResponse = ResearchSessionResponse

# --- Extraction Agent Structured Metric Item ---

class ExtractedMetricItem(BaseModel):
    metric_name: str
    metric_key: str
    value: Optional[Union[float, int, str]] = None
    unit: Optional[str] = None
    financial_year: Optional[str] = None
    source_page: Optional[int] = None
    source_chunk_id: Optional[str] = None
    status: str = "available"  # "available" or "unavailable"
    confidence: Optional[str] = "high"

# --- Financial Document Models ---

class FinancialDocumentResponse(BaseModel):
    id: str = Field(..., description="Unique document identifier")
    session_id: str = Field(..., description="ID of the research session this document belongs to")
    company_name: Optional[str] = Field(None, description="Target company or issuer name")
    document_name: str = Field(..., description="Name of the financial document")
    document_type: str = Field(..., description="Classification type (e.g., Form 10-K, Earnings Call)")
    file_path: str = Field(..., description="Persistent file storage path")
    upload_date: str = Field(..., description="Timestamp when document was uploaded")
    processing_status: ProcessingStatus = Field(..., description="Processing state")
    
    file_size_bytes: int = 0
    file_size: Optional[int] = None
    page_count: int = 0
    word_count: int = 0
    filing_type: Optional[str] = None
    extraction_status: Optional[str] = None
    summary_snippet: Optional[str] = None
    relevance_status: Optional[str] = "FINANCIAL"
    relevance_reason: Optional[str] = None
    relevance_confidence: Optional[str] = "HIGH"
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.filing_type is None:
            self.filing_type = self.document_type
        if self.file_size is None:
            self.file_size = self.file_size_bytes
        if self.extraction_status is None:
            if self.relevance_status == "NON_FINANCIAL":
                self.extraction_status = "Skipped"
            elif self.relevance_status == "UNCERTAIN":
                self.extraction_status = "Not Started"
            else:
                self.extraction_status = "Complete" if self.processing_status in [ProcessingStatus.READY, ProcessingStatus.COMPLETED] else "Pending"

    @property
    def filename(self) -> str:
        return self.document_name

    @property
    def status(self) -> ProcessingStatus:
        return self.processing_status

    @property
    def doc_type(self) -> str:
        return self.document_type

DocumentResponse = FinancialDocumentResponse

class FinancialDocumentUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    document_name: Optional[str] = Field(None, min_length=1, max_length=255)
    document_type: Optional[str] = Field(None, min_length=1, max_length=100)

class DocumentChunk(BaseModel):
    id: str
    chunk_index: int
    content: str
    token_estimate: int
    metadata: Optional[Dict[str, Any]] = None

class FinancialDocumentDetailResponse(FinancialDocumentResponse):
    extracted_text: Optional[str] = None
    financial_metrics: Optional[Any] = None
    structured_metrics: Optional[List[ExtractedMetricItem]] = None
    chunks: List[DocumentChunk] = []

DocumentDetailResponse = FinancialDocumentDetailResponse

class ReprocessRequest(BaseModel):
    force: bool = False

# --- Red Flag Models ---
class RedFlagItem(BaseModel):
    id: str
    session_id: str
    document_id: str
    company_name: Optional[str] = None
    flag_type: str
    title: str
    description: str
    supporting_metrics: List[str] = []
    fiscal_period: Optional[str] = None
    severity: str = "MEDIUM"
    source_page: Optional[int] = None
    source_chunk_id: Optional[str] = None
    evidence_text: Optional[str] = None
    explanation: str
    status: str = "FLAGGED"
    created_at: str

# --- Multi-Agent Orchestration Audit Models ---
class AgentRunItem(BaseModel):
    id: str
    session_id: str
    document_id: str
    agent_name: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    output_summary: Optional[str] = None
    error_message: Optional[str] = None

# --- Research Agent Models ---
class ResearchCitation(BaseModel):
    company_name: Optional[str] = None
    document_name: Optional[str] = None
    source_page: Optional[int] = None
    source_chunk_id: Optional[str] = None
    snippet: Optional[str] = None

class ResearchQueryRequest(BaseModel):
    query: str
    document_id: Optional[str] = None

class ResearchQueryResponse(BaseModel):
    query: str
    sub_questions: List[str] = []
    findings: List[str] = []
    evidence: List[Dict[str, Any]] = []
    answer: str
    sources: List[ResearchCitation] = []
    agent_used: str = "Research Agent"

# --- Comparison Agent Models ---
class ComparisonMetricRow(BaseModel):
    metric_name: str
    metric_key: str
    company_values: Dict[str, Dict[str, Any]]
    difference_note: Optional[str] = None

class ComparisonRequest(BaseModel):
    document_ids: Optional[List[str]] = None

class ComparisonResponse(BaseModel):
    session_id: str
    companies: List[str]
    documents: List[Dict[str, str]]
    metrics_table: List[ComparisonMetricRow]
    executive_comparison: str

# --- Report Agent Models ---
class ReportKeyFinancial(BaseModel):
    metric_name: str
    value: Optional[Union[float, int, str]] = None
    unit: Optional[str] = None
    fiscal_year: Optional[str] = None
    source_page: Optional[int] = None

class GeneratedReportResponse(BaseModel):
    id: str
    session_id: str
    document_id: str
    company_name: Optional[str] = None
    title: str
    executive_summary: str
    key_financials: List[ReportKeyFinancial] = []
    sources: List[ResearchCitation] = []
    created_at: str

