import React, { useState, useEffect } from "react";
import { 
  FileText, 
  Eye, 
  Trash2, 
  Download, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Search, 
  Building, 
  RotateCw, 
  Clock, 
  Pencil, 
  Check, 
  X
} from "lucide-react";
import type { DocumentItem, ProcessingStatus } from "../types";
import { listDocuments, getDownloadUrl, reprocessDocument, updateDocument } from "../services/api";

interface Props {
  sessionId: string;
  onSelectDoc: (docId: string) => void;
  onDeleteDoc: (doc: DocumentItem) => void;
  refreshTrigger: number;
}

export const DocumentList: React.FC<Props> = ({
  sessionId,
  onSelectDoc,
  onDeleteDoc,
  refreshTrigger,
}) => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [reprocessingMap, setReprocessingMap] = useState<Record<string, boolean>>({});
  const [editingDocId, setEditingDocId] = useState<string | null>(null);
  const [editCompanyText, setEditCompanyText] = useState("");
  const [savingCompany, setSavingCompany] = useState(false);

  const startEditCompany = (e: React.MouseEvent, doc: DocumentItem) => {
    e.stopPropagation();
    setEditingDocId(doc.id);
    setEditCompanyText(doc.company_name || "");
  };

  const cancelEditCompany = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setEditingDocId(null);
    setEditCompanyText("");
  };

  const saveEditCompany = async (e: React.MouseEvent | React.KeyboardEvent, docId: string) => {
    e.stopPropagation();
    if (savingCompany) return;
    setSavingCompany(true);
    try {
      const updated = await updateDocument(sessionId, docId, { company_name: editCompanyText.trim() });
      setDocuments((prev) =>
        prev.map((d) => (d.id === docId ? { ...d, company_name: updated.company_name } : d))
      );
      setEditingDocId(null);
    } catch (err) {
      console.error("Failed to update company name", err);
    } finally {
      setSavingCompany(false);
    }
  };

  const fetchDocs = async () => {
    try {
      const data = await listDocuments(sessionId);
      setDocuments(data);
    } catch (err) {
      console.error("Failed to fetch documents", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchDocs();
  }, [sessionId, refreshTrigger]);

  useEffect(() => {
    const hasUnfinished = documents.some((d) => {
      const st = d.processing_status || d.status;
      return ["PENDING", "PROCESSING", "PARSING", "CHUNKING", "EMBEDDING", "INDEXING"].includes(st);
    });
    if (!hasUnfinished) return;

    const interval = setInterval(() => {
      fetchDocs();
    }, 2000);

    return () => clearInterval(interval);
  }, [sessionId, documents]);

  const handleReprocess = async (e: React.MouseEvent, docId: string) => {
    e.stopPropagation();
    setReprocessingMap((prev) => ({ ...prev, [docId]: true }));
    try {
      await reprocessDocument(sessionId, docId);
      await fetchDocs();
    } catch (err) {
      console.error(err);
    } finally {
      setReprocessingMap((prev) => ({ ...prev, [docId]: false }));
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const filtered = documents.filter((doc) => {
    const name = (doc.document_name || doc.filename || "").toLowerCase();
    const type = (doc.document_type || doc.doc_type || "").toLowerCase();
    const company = (doc.company_name || "").toLowerCase();
    const query = searchQuery.toLowerCase();

    const matchesSearch = name.includes(query) || type.includes(query) || company.includes(query);
    const docStatus = doc.processing_status || doc.status;
    const matchesStatus = statusFilter === "ALL" || docStatus === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Simple, clean Document Agent Status: Uploaded -> Parsing -> Chunking -> Embedding -> Indexing -> Indexed
  const renderDocumentAgentStatus = (status: ProcessingStatus) => {
    switch (status) {
      case "READY":
      case "COMPLETED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>Indexed</span>
          </span>
        );
      case "INDEXING":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
            <span>Indexing...</span>
          </span>
        );
      case "EMBEDDING":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
            <span>Embedding...</span>
          </span>
        );
      case "CHUNKING":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
            <span>Chunking...</span>
          </span>
        );
      case "PARSING":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
            <span>Parsing...</span>
          </span>
        );
      case "PENDING":
      case "PROCESSING":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
            <Clock className="w-3 h-3 text-slate-500" />
            <span>Uploaded</span>
          </span>
        );
      case "FAILED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3 h-3 text-rose-600" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
            <span>Uploaded</span>
          </span>
        );
    }
  };

  // Document Relevance Validation & Extraction Status:
  const renderExtractionAgentStatus = (doc: DocumentItem) => {
    const status = (doc.processing_status || doc.status || "PENDING") as ProcessingStatus;
    const relStatus = doc.relevance_status || "FINANCIAL";

    if (relStatus === "NON_FINANCIAL") {
      return (
        <div className="flex flex-col space-y-0.5">
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200 w-fit">
            <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
            <span>Non-Financial</span>
          </span>
          <span className="text-[10px] text-slate-500">Extraction skipped</span>
        </div>
      );
    }

    if (relStatus === "UNCERTAIN") {
      return (
        <div className="flex flex-col space-y-0.5">
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200 w-fit">
            <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
            <span>Type Uncertain</span>
          </span>
          <span className="text-[10px] text-slate-500">Extraction paused</span>
        </div>
      );
    }

    // Default FINANCIAL
    if (status === "READY" || status === "COMPLETED") {
      return (
        <div className="flex flex-col space-y-0.5">
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 w-fit">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>Financial Document</span>
          </span>
          <span className="text-[10px] text-slate-500">Metrics Extracted</span>
        </div>
      );
    }
    if (["PARSING", "CHUNKING", "EMBEDDING", "INDEXING", "PROCESSING"].includes(status)) {
      return (
        <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
          <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
          <span>Extracting...</span>
        </span>
      );
    }
    if (status === "FAILED") {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs text-slate-500">
          <span>Unavailable</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium text-slate-500 bg-slate-100 border border-slate-200">
        <span>Pending Index</span>
      </span>
    );
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
      {/* Table Header & Search Filter */}
      <div className="p-4 border-b border-slate-200 bg-white flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-72">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter documents, companies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition font-sans"
            />
          </div>

          <div className="flex items-center space-x-1 bg-slate-50 border border-slate-200 rounded-lg p-0.5 text-xs">
            {["ALL", "READY", "FAILED"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition cursor-pointer ${
                  statusFilter === st
                    ? "bg-white text-slate-900 shadow-xs border border-slate-200 font-semibold"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {st === "READY" ? "Indexed" : st === "ALL" ? "All" : "Failed"}
              </button>
            ))}
          </div>
        </div>

        <div className="text-xs text-slate-500 flex items-center space-x-1.5">
          <span>
            Showing <strong className="text-slate-800 font-semibold">{filtered.length}</strong> of{" "}
            <strong className="text-slate-800 font-semibold">{documents.length}</strong> {documents.length === 1 ? "document" : "documents"}
          </span>
        </div>
      </div>

      {/* Financial Documents Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-700">
          <thead className="bg-slate-50/80 text-slate-500 uppercase text-[10px] tracking-wider border-b border-slate-200 font-semibold">
            <tr>
              <th className="py-3 px-4">Document Name</th>
              <th className="py-3 px-4">Company</th>
              <th className="py-3 px-4">Type</th>
              <th className="py-3 px-4">Pages & Size</th>
              <th className="py-3 px-4">Document Agent</th>
              <th className="py-3 px-4">Extraction Agent</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-sans">
            {loading ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-500">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                    <span className="text-xs">Loading financial documents...</span>
                  </div>
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-500">
                  <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="font-semibold text-slate-700">No documents in this session</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {documents.length === 0
                      ? "Upload a financial PDF above to start Document & Extraction analysis."
                      : "No documents matched your search filter."}
                  </p>
                </td>
              </tr>
            ) : (
              filtered.map((doc) => {
                const isReprocessing = !!reprocessingMap[doc.id];
                const displayName = doc.document_name || doc.filename || "Financial Document";
                const displayType = doc.document_type || doc.doc_type || "Annual Report";
                const displayStatus = (doc.processing_status || doc.status || "PENDING") as ProcessingStatus;
                const pageCount = doc.page_count || 1;

                return (
                  <tr
                    key={doc.id}
                    onClick={() => onSelectDoc(doc.id)}
                    className="hover:bg-slate-50/80 cursor-pointer transition group"
                  >
                    {/* Document Name */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center space-x-3 min-w-0">
                        <div className="p-1.5 rounded-lg bg-slate-100 text-slate-600 shrink-0">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <div className="font-semibold text-slate-900 group-hover:text-blue-600 truncate max-w-xs sm:max-w-sm">
                            {displayName}
                          </div>
                          {doc.summary_snippet && (
                            <p className="text-[11px] text-slate-400 line-clamp-1 mt-0.5 max-w-sm">
                              {doc.summary_snippet}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Company */}
                    <td className="py-3.5 px-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      {editingDocId === doc.id ? (
                        <div className="flex items-center space-x-1.5">
                          <input
                            type="text"
                            value={editCompanyText}
                            onChange={(e) => setEditCompanyText(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") saveEditCompany(e, doc.id);
                              if (e.key === "Escape") cancelEditCompany(e as any);
                            }}
                            placeholder="Company name"
                            autoFocus
                            className="bg-white border border-blue-500 rounded px-2 py-0.5 text-xs text-slate-900 focus:outline-none w-36 shadow-xs"
                          />
                          <button
                            onClick={(e) => saveEditCompany(e, doc.id)}
                            disabled={savingCompany}
                            className="p-1 rounded text-emerald-600 hover:bg-emerald-50 transition cursor-pointer"
                            title="Save Company"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => cancelEditCompany(e)}
                            disabled={savingCompany}
                            className="p-1 rounded text-slate-400 hover:bg-slate-100 transition cursor-pointer"
                            title="Cancel"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center space-x-1.5 group/company">
                          {doc.company_name ? (
                            <span className="font-medium text-slate-800 inline-flex items-center space-x-1.5">
                              <Building className="w-3.5 h-3.5 text-slate-500" />
                              <span>{doc.company_name}</span>
                            </span>
                          ) : (
                            <span className="text-slate-400 italic">No company</span>
                          )}
                          <button
                            onClick={(e) => startEditCompany(e, doc)}
                            className="opacity-0 group-hover/company:opacity-100 p-1 text-slate-400 hover:text-slate-700 transition cursor-pointer"
                            title="Edit company name"
                          >
                            <Pencil className="w-3 h-3" />
                          </button>
                        </div>
                      )}
                    </td>

                    {/* Document Type */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                        {displayType}
                      </span>
                    </td>

                    {/* Page count & File size */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="font-medium text-slate-800">
                        {pageCount} {pageCount === 1 ? "page" : "pages"}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {formatBytes(doc.file_size_bytes)}
                      </div>
                    </td>

                    {/* Document Agent Status */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {renderDocumentAgentStatus(displayStatus)}
                    </td>

                    {/* Extraction Agent Status */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {renderExtractionAgentStatus(doc)}
                    </td>

                    {/* Actions with prominent [View] button */}
                    <td className="py-3.5 px-4 whitespace-nowrap text-right">
                      <div 
                        className="flex items-center justify-end space-x-1.5" 
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() => onSelectDoc(doc.id)}
                          className="px-2.5 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium flex items-center space-x-1 shadow-xs cursor-pointer transition"
                          title="View Extracted Metrics & Details"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View</span>
                        </button>

                        <a
                          href={getDownloadUrl(sessionId, doc.id)}
                          download={displayName}
                          className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
                          title="Download PDF"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>

                        <button
                          onClick={(e) => handleReprocess(e, doc.id)}
                          disabled={isReprocessing}
                          className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"
                          title="Reprocess Document"
                        >
                          <RotateCw className={`w-3.5 h-3.5 ${isReprocessing ? "animate-spin" : ""}`} />
                        </button>

                        <button
                          onClick={() => onDeleteDoc(doc)}
                          className="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition cursor-pointer"
                          title="Delete Document"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
