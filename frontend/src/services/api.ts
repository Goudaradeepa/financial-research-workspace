import type { 
  ResearchSession, 
  DocumentItem, 
  DocumentDetail, 
  CreateSessionInput,
  ExtractedMetric,
  RedFlagItem,
  AgentRunItem,
  ComparisonResponse,
  GeneratedReportResponse
} from "../types";

const BASE_URL = "/api";

export async function listSessions(): Promise<ResearchSession[]> {
  const res = await fetch(`${BASE_URL}/sessions`);
  if (!res.ok) throw new Error("Failed to fetch research sessions");
  return res.json();
}

export async function getSession(sessionId: string): Promise<ResearchSession> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch session details");
  return res.json();
}

export async function createSession(input: CreateSessionInput): Promise<ResearchSession> {
  const res = await fetch(`${BASE_URL}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to create session" }));
    throw new Error(err.detail || "Failed to create session");
  }
  return res.json();
}

export async function updateSession(
  sessionId: string,
  input: Partial<CreateSessionInput>
): Promise<ResearchSession> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error("Failed to update session");
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete session");
}

export async function listDocuments(sessionId: string): Promise<DocumentItem[]> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

export async function getDocument(sessionId: string, docId: string): Promise<DocumentDetail> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents/${docId}`);
  if (!res.ok) throw new Error("Failed to fetch document details");
  return res.json();
}

export async function uploadDocuments(
  sessionId: string,
  files: File[],
  companyName?: string,
  companyNames?: Record<string, string>
): Promise<DocumentItem[]> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  if (companyName && companyName.trim()) {
    formData.append("company_name", companyName.trim());
  }
  if (companyNames) {
    formData.append("company_names", JSON.stringify(companyNames));
  }

  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to upload documents" }));
    throw new Error(err.detail || "Failed to upload documents");
  }
  return res.json();
}

export async function updateDocument(
  sessionId: string,
  docId: string,
  input: { company_name?: string; document_name?: string; document_type?: string }
): Promise<DocumentItem> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents/${docId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to update document" }));
    throw new Error(err.detail || "Failed to update document");
  }
  return res.json();
}

export async function deleteDocument(sessionId: string, docId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents/${docId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete document");
}

export async function reprocessDocument(sessionId: string, docId: string): Promise<DocumentItem> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents/${docId}/reprocess`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to reprocess document");
  return res.json();
}

export async function getExtractedMetrics(
  sessionId: string,
  docId: string
): Promise<ExtractedMetric[]> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents/${docId}/metrics`);
  if (!res.ok) throw new Error("Failed to fetch extracted metrics");
  return res.json();
}

export async function triggerExtraction(
  sessionId: string,
  docId: string
): Promise<ExtractedMetric[]> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents/${docId}/extract-metrics`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to run extraction agent");
  return res.json();
}

export function getDownloadUrl(sessionId: string, docId: string): string {
  return `${BASE_URL}/sessions/${sessionId}/documents/${docId}/download`;
}

// --- Red Flag Agent APIs ---
export async function listDocumentRedFlags(sessionId: string, docId: string): Promise<RedFlagItem[]> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents/${docId}/red-flags`);
  if (!res.ok) throw new Error("Failed to fetch document red flags");
  return res.json();
}

export async function listSessionRedFlags(sessionId: string): Promise<RedFlagItem[]> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/red-flags`);
  if (!res.ok) throw new Error("Failed to fetch session red flags");
  return res.json();
}

export async function triggerRedFlagAnalysis(sessionId: string, docId: string): Promise<RedFlagItem[]> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents/${docId}/red-flags/analyze`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to run red flag analysis");
  return res.json();
}

// --- Multi-Agent Orchestrator Audit APIs ---
export async function listDocumentAgentRuns(sessionId: string, docId: string): Promise<AgentRunItem[]> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents/${docId}/agent-runs`);
  if (!res.ok) throw new Error("Failed to fetch agent runs");
  return res.json();
}

export async function listSessionAgentRuns(sessionId: string): Promise<AgentRunItem[]> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/agent-runs`);
  if (!res.ok) throw new Error("Failed to fetch session agent runs");
  return res.json();
}

// --- Conversational Research & Chat APIs ---
export async function sendChatMessage(
  sessionId: string,
  message: string,
  docId?: string
): Promise<{ message: string; intent: string; answer: string; sources: any[]; agent_used: string; suggested_queries?: string[] }> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, document_id: docId }),
  });
  if (!res.ok) throw new Error("Failed to process conversational research query");
  return res.json();
}

export async function getChatHistory(sessionId: string): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/chat/history`);
  if (!res.ok) throw new Error("Failed to fetch chat history");
  return res.json();
}

// --- Comparison Agent APIs ---
export async function compareDocuments(
  sessionId: string,
  documentIds?: string[]
): Promise<ComparisonResponse> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_ids: documentIds }),
  });
  if (!res.ok) throw new Error("Failed to run comparison agent");
  return res.json();
}

// --- Report Agent APIs ---
export async function generateReport(
  sessionId: string,
  docId: string
): Promise<GeneratedReportResponse> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents/${docId}/report`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to generate report");
  return res.json();
}

export async function getReport(
  sessionId: string,
  docId: string
): Promise<GeneratedReportResponse | null> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/documents/${docId}/report`);
  if (!res.ok) return null;
  return res.json();
}

