import React, { useState, useEffect } from "react";
import { 
  X, 
  FileText, 
  Download, 
  Copy, 
  Check, 
  RotateCw, 
  Layers, 
  AlertCircle,
  Building,
  BarChart2,
  ExternalLink,
  ShieldCheck,
  Search,
  CheckCircle2
} from "lucide-react";
import type { DocumentDetail } from "../types";
import { getDocument, getDownloadUrl, triggerExtraction } from "../services/api";

interface Props {
  sessionId: string;
  documentId: string | null;
  onClose: () => void;
  onDocumentUpdated?: () => void;
}

export const DocumentPreviewModal: React.FC<Props> = ({
  sessionId,
  documentId,
  onClose,
  onDocumentUpdated,
}) => {
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"metrics" | "content" | "technical">("metrics");
  const [copied, setCopied] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [highlightPage, setHighlightPage] = useState<number | null>(null);

  useEffect(() => {
    if (!documentId) {
      setDoc(null);
      return;
    }

    const fetchDoc = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getDocument(sessionId, documentId);
        setDoc(data);
      } catch (err: any) {
        setError(err.message || "Failed to load document preview");
      } finally {
        setLoading(false);
      }
    };

    fetchDoc();
  }, [sessionId, documentId]);

  if (!documentId) return null;

  const handleCopy = () => {
    if (!doc?.extracted_text) return;
    navigator.clipboard.writeText(doc.extracted_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTriggerExtraction = async () => {
    if (!doc) return;
    setExtracting(true);
    try {
      await triggerExtraction(sessionId, doc.id);
      const updated = await getDocument(sessionId, doc.id);
      setDoc(updated);
      onDocumentUpdated?.();
    } catch (err) {
      console.error(err);
    } finally {
      setExtracting(false);
    }
  };

  const jumpToPage = (pageNum: number) => {
    setHighlightPage(pageNum);
    setActiveTab("content");
    setTimeout(() => {
      const el = document.getElementById(`doc-page-${pageNum}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 100);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const formatValue = (val: any, unit?: string | null) => {
    if (val === null || val === undefined) return null;
    if (typeof val === "number") {
      const formatted = val.toLocaleString(undefined, { maximumFractionDigits: 2 });
      if (unit === "%") return `${formatted}%`;
      if (unit === "$B") return `$${formatted}B`;
      if (unit === "$M") return `$${formatted}M`;
      if (unit === "$/share") return `$${formatted}/share`;
      return `${formatted} ${unit || ""}`.trim();
    }
    return String(val);
  };

  const metricsList = doc?.structured_metrics || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-3 md:p-6">
      <div className="bg-white border border-slate-200 w-full max-w-5xl h-[88vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 bg-white flex items-start justify-between shrink-0">
          <div className="min-w-0 flex-1 mr-4">
            <div className="flex items-center space-x-2 flex-wrap gap-y-1 mb-1.5">
              {doc?.company_name && (
                <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold flex items-center space-x-1">
                  <Building className="w-3 h-3 text-blue-600" />
                  <span>{doc.company_name}</span>
                </span>
              )}
              <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium">
                {doc?.document_type || "Financial Document"}
              </span>
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                <span>Indexed</span>
              </span>

              {doc?.relevance_status === "NON_FINANCIAL" ? (
                <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
                  <AlertCircle className="w-3 h-3 text-amber-600" />
                  <span>Non-Financial Document (Extraction skipped)</span>
                </span>
              ) : doc?.relevance_status === "UNCERTAIN" ? (
                <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
                  <AlertCircle className="w-3 h-3 text-amber-600" />
                  <span>Document Type Uncertain</span>
                </span>
              ) : (
                <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  <span>Financial Document</span>
                </span>
              )}
            </div>

            <h3 className="text-base font-bold text-slate-900 truncate" title={doc?.document_name}>
              {doc?.document_name}
            </h3>

            <div className="flex items-center space-x-3 text-xs text-slate-500 mt-1">
              <span>{doc?.page_count || 1} pages</span>
              <span>•</span>
              <span>{formatBytes(doc?.file_size_bytes || 0)}</span>
              <span>•</span>
              <span>Document Agent & Extraction Agent Verified</span>
            </div>
          </div>

          <div className="flex items-center space-x-1.5 shrink-0">
            {doc && (
              <a
                href={getDownloadUrl(sessionId, doc.id)}
                download={doc.document_name}
                className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition"
                title="Download PDF"
              >
                <Download className="w-4 h-4" />
              </a>
            )}
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Clean Workspace Tabs */}
        <div className="px-6 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setActiveTab("metrics")}
              className={`py-3 text-xs font-medium border-b-2 transition flex items-center space-x-1.5 cursor-pointer ${
                activeTab === "metrics"
                  ? "border-blue-600 text-blue-700 font-semibold"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5 text-blue-600" />
              <span>Financial Metrics</span>
            </button>

            <button
              onClick={() => setActiveTab("content")}
              className={`py-3 text-xs font-medium border-b-2 transition flex items-center space-x-1.5 cursor-pointer ${
                activeTab === "content"
                  ? "border-blue-600 text-blue-700 font-semibold"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <FileText className="w-3.5 h-3.5 text-slate-500" />
              <span>Document Text</span>
            </button>

            <button
              onClick={() => setActiveTab("technical")}
              className={`py-3 text-xs font-medium border-b-2 transition flex items-center space-x-1.5 cursor-pointer ${
                activeTab === "technical"
                  ? "border-blue-600 text-blue-700 font-semibold"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <Layers className="w-3.5 h-3.5 text-slate-500" />
              <span>Technical Details</span>
            </button>
          </div>

          <div className="flex items-center space-x-2 py-1.5">
            {activeTab === "metrics" && (
              <button
                onClick={handleTriggerExtraction}
                disabled={extracting || doc?.relevance_status === "NON_FINANCIAL"}
                className={`text-xs flex items-center space-x-1.5 px-3 py-1 rounded-lg border transition shadow-xs cursor-pointer ${
                  doc?.relevance_status === "NON_FINANCIAL"
                    ? "opacity-40 cursor-not-allowed text-slate-400 border-slate-200 bg-slate-100"
                    : "text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border-slate-300 font-medium"
                }`}
                title={doc?.relevance_status === "NON_FINANCIAL" ? "Financial extraction skipped for non-financial documents" : "Re-Run Extraction"}
              >
                <RotateCw className={`w-3.5 h-3.5 ${extracting ? "animate-spin" : ""}`} />
                <span>{extracting ? "Extracting..." : "Re-Run Extraction"}</span>
              </button>
            )}

            {activeTab === "content" && doc?.extracted_text && (
              <button
                onClick={handleCopy}
                className="text-xs text-slate-600 hover:text-slate-900 flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 transition cursor-pointer"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? "Copied" : "Copy Text"}</span>
              </button>
            )}
          </div>
        </div>

        {/* Tab Body */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50/50 font-sans">
          {loading ? (
            <div className="h-full flex flex-col items-center justify-center space-y-2 text-slate-500">
              <RotateCw className="w-6 h-6 animate-spin text-blue-600" />
              <p className="text-xs">Loading document data...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 shrink-0 text-rose-600" />
              <span>{error}</span>
            </div>
          ) : activeTab === "metrics" ? (
            /* TAB 1: FINANCIAL METRICS (EXTRACTION AGENT) */
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
                <div>
                  <h4 className="text-xs font-bold text-slate-900 flex items-center space-x-1.5">
                    <ShieldCheck className="w-4 h-4 text-blue-600" />
                    <span>Grounded Financial Metrics</span>
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Structured metrics extracted with page citations and vector chunk provenance.
                  </p>
                </div>
                <div className="text-[11px] text-slate-500 bg-slate-50 px-2.5 py-1 rounded-md border border-slate-200">
                  Strictly Grounded
                </div>
              </div>

              {doc?.relevance_status === "NON_FINANCIAL" ? (
                <div className="py-12 px-6 text-center max-w-lg mx-auto bg-amber-50 border border-amber-200 rounded-2xl my-6">
                  <AlertCircle className="w-9 h-9 text-amber-600 mx-auto mb-2.5" />
                  <h4 className="text-sm font-bold text-amber-900">Non-Financial Document</h4>
                  <p className="text-xs text-amber-800 mt-1">
                    This PDF does not appear to be a financial document. Financial analysis was skipped.
                  </p>
                  {doc?.relevance_reason && (
                    <p className="text-[11px] text-slate-600 mt-3 p-3 rounded-xl bg-white border border-amber-200 text-left">
                      <strong>Validation reason:</strong> {doc.relevance_reason}
                    </p>
                  )}
                </div>
              ) : doc?.relevance_status === "UNCERTAIN" ? (
                <div className="py-12 px-6 text-center max-w-lg mx-auto bg-amber-50 border border-amber-200 rounded-2xl my-6">
                  <AlertCircle className="w-9 h-9 text-amber-600 mx-auto mb-2.5" />
                  <h4 className="text-sm font-bold text-amber-900">Document Type Uncertain</h4>
                  <p className="text-xs text-amber-800 mt-1">
                    Unable to confidently determine whether this document is a financial report. Financial analysis not started.
                  </p>
                  {doc?.relevance_reason && (
                    <p className="text-[11px] text-slate-600 mt-3 p-3 rounded-xl bg-white border border-amber-200 text-left">
                      <strong>Validation reason:</strong> {doc.relevance_reason}
                    </p>
                  )}
                </div>
              ) : metricsList.length === 0 ? (
                <div className="py-12 text-center text-slate-500">
                  <BarChart2 className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="font-semibold text-slate-700">No metrics extracted yet</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Click "Re-Run Extraction" to retrieve financial metrics from the document.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-xs">
                  <table className="w-full text-left text-xs text-slate-700">
                    <thead className="bg-slate-50/80 text-slate-500 uppercase text-[10px] tracking-wider border-b border-slate-200 font-semibold">
                      <tr>
                        <th className="py-3 px-4">Financial Metric</th>
                        <th className="py-3 px-4">Extracted Value</th>
                        <th className="py-3 px-4">Unit</th>
                        <th className="py-3 px-4">Fiscal Period</th>
                        <th className="py-3 px-4">Source Reference</th>
                        <th className="py-3 px-4 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-sans">
                      {metricsList.map((m, idx) => {
                        const isAvailable = m.value !== null && m.value !== undefined;
                        const formatted = formatValue(m.value, m.unit);

                        return (
                          <tr key={idx} className="hover:bg-slate-50/70 transition">
                            {/* Metric Name */}
                            <td className="py-3 px-4 font-semibold text-slate-900">
                              {m.metric_name}
                            </td>

                            {/* Value */}
                            <td className="py-3 px-4 font-mono font-bold">
                              {isAvailable ? (
                                <span className="text-slate-900 text-sm">
                                  {formatted}
                                </span>
                              ) : (
                                <span className="text-slate-400 italic">Not reported</span>
                              )}
                            </td>

                            {/* Unit */}
                            <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                              {m.unit || "—"}
                            </td>

                            {/* Fiscal Year */}
                            <td className="py-3 px-4 text-slate-600">
                              {m.financial_year ? `FY${m.financial_year}` : "—"}
                            </td>

                            {/* Source Page with clickable jump button */}
                            <td className="py-3 px-4 whitespace-nowrap">
                              {m.source_page ? (
                                <button
                                  onClick={() => jumpToPage(m.source_page!)}
                                  className="px-2 py-0.5 rounded bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 transition text-xs font-medium flex items-center space-x-1 cursor-pointer"
                                  title={`Jump to Page ${m.source_page} in Document Text`}
                                >
                                  <span>Page {m.source_page}</span>
                                  <ExternalLink className="w-3 h-3" />
                                </button>
                              ) : (
                                <span className="text-slate-400 text-xs">—</span>
                              )}
                            </td>

                            {/* Status Badge */}
                            <td className="py-3 px-4 text-right whitespace-nowrap">
                              {isAvailable ? (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                                  Available
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-500 border border-slate-200">
                                  Not Reported
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : activeTab === "content" ? (
            /* TAB 2: DOCUMENT TEXT (PRESERVED PAGE NUMBERS) */
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3 p-3 rounded-xl bg-white border border-slate-200 shadow-xs">
                <div className="relative flex-1 max-w-sm">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                  <input
                    type="text"
                    placeholder="Search in document text..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-blue-500 transition"
                  />
                </div>
                {highlightPage && (
                  <button
                    onClick={() => setHighlightPage(null)}
                    className="text-xs text-blue-600 hover:text-blue-700 font-medium cursor-pointer"
                  >
                    Clear Page Filter (Viewing Page {highlightPage})
                  </button>
                )}
              </div>

              <div className="space-y-4">
                {doc?.extracted_text ? (
                  doc.extracted_text
                    .split(/--- \[Page (\d+)\] ---/)
                    .slice(1)
                    .reduce<{ page: number; text: string }[]>((acc, cur, idx, arr) => {
                      if (idx % 2 === 0) {
                        acc.push({
                          page: parseInt(cur, 10),
                          text: arr[idx + 1] || "",
                        });
                      }
                      return acc;
                    }, [])
                    .filter((p) => !highlightPage || p.page === highlightPage)
                    .filter((p) => !searchTerm || p.text.toLowerCase().includes(searchTerm.toLowerCase()))
                    .map((p) => (
                      <div
                        key={p.page}
                        id={`doc-page-${p.page}`}
                        className={`rounded-xl border p-5 transition shadow-xs ${
                          highlightPage === p.page
                            ? "bg-blue-50/50 border-blue-400 ring-1 ring-blue-400"
                            : "bg-white border-slate-200"
                        }`}
                      >
                        <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-slate-100 text-xs">
                          <span className="font-bold text-blue-700 font-mono">
                            Page {p.page}
                          </span>
                          <span className="text-[11px] text-slate-400">
                            Preserved by Document Agent
                          </span>
                        </div>
                        <pre className="font-sans text-xs text-slate-800 whitespace-pre-wrap leading-relaxed">
                          {p.text.trim()}
                        </pre>
                      </div>
                    ))
                ) : (
                  <div className="py-12 text-center text-slate-500">
                    No extracted text available for this document.
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* TAB 3: TECHNICAL DETAILS */
            <div className="space-y-4 text-xs">
              <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
                <h4 className="font-bold text-slate-900 mb-2.5">Document Processing Provenance</h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-slate-600">
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Document ID</span>
                    <span className="font-mono text-slate-800">{doc?.id}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Total Pages</span>
                    <span className="text-slate-800 font-medium">{doc?.page_count}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Total Words</span>
                    <span className="text-slate-800 font-medium">{doc?.word_count?.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Storage Path</span>
                    <span className="font-mono text-[10px] text-slate-700 truncate block" title={doc?.file_path}>
                      {doc?.file_path}
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
                <h4 className="font-bold text-slate-900 mb-2.5">FAISS Vector Index Chunks ({doc?.chunks?.length || 0})</h4>
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {doc?.chunks && doc.chunks.length > 0 ? (
                    doc.chunks.map((chunk, cIdx) => (
                      <div key={chunk.id || cIdx} className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                        <div className="flex items-center justify-between text-[10px] text-slate-500 mb-1 font-mono">
                          <span>Chunk ID: {chunk.id}</span>
                          <span>~{chunk.token_estimate} tokens</span>
                        </div>
                        <p className="text-slate-700 text-xs line-clamp-3 leading-relaxed">
                          {chunk.content}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-slate-400 italic">No vector chunks available.</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
