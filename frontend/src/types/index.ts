export type ProcessingStatus = 
  | "PENDING" 
  | "PROCESSING" 
  | "PARSING" 
  | "CHUNKING" 
  | "EMBEDDING" 
  | "INDEXING" 
  | "READY" 
  | "COMPLETED" 
  | "FAILED";

export interface ResearchSession {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  ticker?: string | null;
  tags: string[];
  document_count: number;
  total_size_bytes: number;
}

export interface ExtractedMetric {
  metric_name: string;
  metric_key: string;
  value: number | string | null;
  unit?: string | null;
  financial_year?: string | null;
  source_page?: number | null;
  source_chunk_id?: string | null;
  status: "available" | "unavailable";
  confidence?: string | null;
}

export interface DocumentItem {
  id: string;
  session_id: string;
  company_name?: string | null;
  document_name: string;
  document_type: string;
  file_path: string;
  upload_date: string;
  processing_status: ProcessingStatus;
  
  filename?: string;
  status?: ProcessingStatus;
  doc_type?: string | null;
  file_type?: string;
  file_size_bytes: number;
  page_count: number;
  word_count: number;
  summary_snippet?: string | null;
  error_message?: string | null;
  relevance_status?: "FINANCIAL" | "NON_FINANCIAL" | "UNCERTAIN" | string | null;
  relevance_reason?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface DocumentChunk {
  id: string;
  chunk_index: number;
  content: string;
  token_estimate: number;
  metadata?: Record<string, any> | null;
}

export interface DocumentDetail extends DocumentItem {
  extracted_text?: string | null;
  financial_metrics?: any;
  structured_metrics?: ExtractedMetric[] | null;
  chunks: DocumentChunk[];
}

export interface CreateSessionInput {
  name: string;
  description?: string;
  ticker?: string;
  tags?: string[];
}

export interface RedFlagItem {
  id: string;
  session_id: string;
  document_id: string;
  company_name?: string | null;
  flag_type: string;
  title: string;
  description: string;
  supporting_metrics: string[];
  fiscal_period?: string | null;
  severity: "HIGH" | "MEDIUM" | "LOW" | "INFO";
  source_page?: number | null;
  source_chunk_id?: string | null;
  evidence_text?: string | null;
  explanation: string;
  status: "FLAGGED" | "INSUFFICIENT_EVIDENCE" | "CLEAN";
  created_at: string;
}

export interface AgentRunItem {
  id: string;
  session_id: string;
  document_id: string;
  agent_name: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  started_at: string;
  completed_at?: string | null;
  output_summary?: string | null;
  error_message?: string | null;
}

export interface ResearchCitation {
  company_name?: string | null;
  document_name?: string | null;
  source_page?: number | null;
  source_chunk_id?: string | null;
  snippet?: string | null;
}

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  agent_used?: string;
  intent?: string;
  sources?: ResearchCitation[];
  suggested_queries?: string[];
  timestamp?: string;
}

export interface ComparisonMetricCompanyVal {
  value: number | string | null;
  unit?: string | null;
  fiscal_year?: string | null;
  source_page?: number | null;
  status: string;
  display?: string;
}

export interface ComparisonMetricRow {
  metric_name: string;
  metric_key: string;
  company_values: Record<string, ComparisonMetricCompanyVal>;
  difference_note?: string | null;
}

export interface ComparisonResponse {
  session_id: string;
  companies: string[];
  documents: { document_id: string; company_name: string; document_name: string }[];
  metrics_table: ComparisonMetricRow[];
  executive_comparison: string;
}

export interface ReportKeyFinancial {
  metric_name: string;
  value: number | string | null;
  unit?: string | null;
  fiscal_year?: string | null;
  source_page?: number | null;
}

export interface GeneratedReportResponse {
  id: string;
  session_id: string;
  document_id: string;
  company_name?: string | null;
  title: string;
  executive_summary: string;
  key_financials: ReportKeyFinancial[];
  sources: ResearchCitation[];
  created_at: string;
}

