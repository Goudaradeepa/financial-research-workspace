import React, { useState, useRef } from "react";
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2, Building, X, ArrowRight } from "lucide-react";
import { uploadDocuments } from "../services/api";
import type { DocumentItem } from "../types";

interface Props {
  sessionId: string;
  onUploadSuccess: (docs: DocumentItem[]) => void;
}

interface StagedFile {
  file: File;
  companyName: string;
  documentType: string;
  isAutoDetected: boolean;
}

function guessCompanyFromFilename(filename: string): string {
  const name = filename.toLowerCase();
  if (name.includes("cognizant") || name.includes("ctsh")) return "Cognizant";
  if (name.includes("tata consultancy") || name.includes("tcs")) return "Tata Consultancy Services";
  if (name.includes("infosys") || name.includes("infy")) return "Infosys";
  if (name.includes("wipro")) return "Wipro";
  if (name.includes("apple") || name.includes("aapl")) return "Apple";
  if (name.includes("microsoft") || name.includes("msft")) return "Microsoft";
  if (name.includes("tesla") || name.includes("tsla")) return "Tesla";
  if (name.includes("nvidia") || name.includes("nvda")) return "NVIDIA";
  if (name.includes("amazon") || name.includes("amzn")) return "Amazon";
  if (name.includes("google") || name.includes("alphabet") || name.includes("goog")) return "Alphabet";
  if (name.includes("meta") || name.includes("facebook")) return "Meta";
  if (name.includes("reliance") || name.includes("ril")) return "Reliance Industries";
  if (name.includes("hdfc")) return "HDFC Bank";
  if (name.includes("icici")) return "ICICI Bank";

  // Match pattern like "Company Name Annual Report..."
  const clean = filename.replace(/\.pdf$/i, "").replace(/[_-]/g, " ");
  const match = clean.match(/^([A-Za-z\s]+?)(?:\s+(?:annual\s+report|10-k|10-q|integrated|financial|q[1-4]|fy\d{2,4}|\d{4}))/i);
  if (match && match[1].trim().length > 2) {
    return match[1].trim();
  }
  return "";
}

function guessDocumentType(filename: string): string {
  const lower = filename.toLowerCase();
  if (lower.includes("10-k")) return "10-K Filing";
  if (lower.includes("10-q")) return "10-Q Filing";
  if (lower.includes("integrated")) return "Integrated Annual Report";
  if (lower.includes("quarterly") || lower.includes("q1") || lower.includes("q2") || lower.includes("q3") || lower.includes("q4")) return "Quarterly Report";
  return "Annual Report";
}

export const DocumentUpload: React.FC<Props> = ({ sessionId, onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccessMsg, setUploadSuccessMsg] = useState<string | null>(null);
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const handleFilesSelected = (files: FileList | File[]) => {
    const rawFiles = Array.from(files);
    if (rawFiles.length === 0) return;

    // Filter strictly for PDF files only
    const nonPdfFiles = rawFiles.filter(
      (f) => !f.name.toLowerCase().endsWith(".pdf") && f.type !== "application/pdf"
    );

    if (nonPdfFiles.length > 0) {
      setUploadError("Only PDF financial documents are supported. Please select .pdf files only.");
      return;
    }

    setUploadError(null);
    setUploadSuccessMsg(null);

    const staged: StagedFile[] = rawFiles.map((f) => {
      const guessed = guessCompanyFromFilename(f.name);
      return {
        file: f,
        companyName: guessed,
        documentType: guessDocumentType(f.name),
        isAutoDetected: !!guessed,
      };
    });

    setStagedFiles((prev) => [...prev, ...staged]);
  };

  const updateStagedCompany = (index: number, newCompany: string) => {
    setStagedFiles((prev) =>
      prev.map((item, idx) =>
        idx === index ? { ...item, companyName: newCompany, isAutoDetected: false } : item
      )
    );
  };

  const removeStagedFile = (index: number) => {
    setStagedFiles((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleUploadStaged = async () => {
    if (stagedFiles.length === 0) return;

    setUploading(true);
    setUploadError(null);
    setUploadSuccessMsg(null);

    try {
      const files = stagedFiles.map((s) => s.file);
      const companyNames: Record<string, string> = {};
      stagedFiles.forEach((s) => {
        if (s.companyName.trim()) {
          companyNames[s.file.name] = s.companyName.trim();
        }
      });

      const singleCompany = stagedFiles.length === 1 ? stagedFiles[0].companyName.trim() : undefined;

      const createdDocs = await uploadDocuments(
        sessionId,
        files,
        singleCompany,
        companyNames
      );

      setStagedFiles([]);
      setUploadSuccessMsg(
        `Successfully uploaded ${createdDocs.length} PDF report(s). Document Agent is indexing and extracting metrics...`
      );
      onUploadSuccess(createdDocs);
      setTimeout(() => setUploadSuccessMsg(null), 4500);
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload document(s)");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelected(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 mb-6 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
            <UploadCloud className="w-4 h-4 text-blue-600" />
            <span>Upload Financial Documents</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Supported format: <strong className="text-slate-700 font-medium">PDF</strong> (Annual Reports, Form 10-K, Form 10-Q). Automatic company detection and relevance validation.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => !uploading && fileInputRef.current?.click()}
            disabled={uploading}
            className="px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-medium transition flex items-center space-x-1.5 shadow-xs cursor-pointer"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Select PDF</span>
          </button>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        accept=".pdf,application/pdf"
        onChange={(e) => e.target.files && handleFilesSelected(e.target.files)}
      />

      {/* Dropzone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !uploading && fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition flex flex-col items-center justify-center ${
          isDragging
            ? "border-blue-500 bg-blue-50/60"
            : "border-slate-200 hover:border-slate-300 bg-slate-50/50 hover:bg-slate-50"
        } ${uploading ? "opacity-60 pointer-events-none" : ""}`}
      >
        <div className="flex flex-col items-center py-1 space-y-2">
          <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center">
            <UploadCloud className="w-5 h-5" />
          </div>
          <div className="text-xs font-medium text-slate-700">
            Drag and drop financial PDF filings here, or{" "}
            <span className="text-blue-600 font-semibold hover:underline">browse files</span>
          </div>
          <div className="text-[11px] text-slate-400">
            PDF text extraction, chunking, FAISS indexing, and financial metric extraction
          </div>
        </div>
      </div>

      {/* Staged Files Review & Company Confirmation Panel */}
      {stagedFiles.length > 0 && (
        <div className="mt-4 p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200">
            <div className="flex items-center space-x-2">
              <Building className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-semibold text-slate-800">
                Confirm Document Details ({stagedFiles.length} file{stagedFiles.length > 1 ? "s" : ""})
              </span>
            </div>
            <button
              onClick={() => setStagedFiles([])}
              disabled={uploading}
              className="text-[11px] text-slate-500 hover:text-rose-600 transition cursor-pointer"
            >
              Clear all
            </button>
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {stagedFiles.map((staged, idx) => (
              <div
                key={idx}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-white border border-slate-200 rounded-lg text-xs"
              >
                <div className="flex items-center space-x-2.5 min-w-0 flex-1">
                  <div className="p-1.5 rounded-md bg-slate-100 text-slate-600 shrink-0">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900 truncate max-w-xs sm:max-w-md" title={staged.file.name}>
                      {staged.file.name}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      {formatBytes(staged.file.size)} • {staged.documentType}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-2 shrink-0">
                  <div className="flex flex-col">
                    <div className="flex items-center space-x-1.5">
                      <span className="text-[10px] text-slate-500 uppercase font-semibold">Company:</span>
                      {staged.isAutoDetected && (
                        <span className="px-1.5 py-0.2 rounded text-[9px] bg-blue-50 text-blue-700 border border-blue-200 font-medium">
                          Auto-detected
                        </span>
                      )}
                    </div>
                    <input
                      type="text"
                      value={staged.companyName}
                      onChange={(e) => updateStagedCompany(idx, e.target.value)}
                      placeholder="e.g. Apple, Microsoft"
                      className="mt-0.5 bg-white border border-slate-300 rounded px-2.5 py-1 text-xs text-slate-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 w-48 placeholder-slate-400"
                    />
                  </div>

                  <button
                    onClick={() => removeStagedFile(idx)}
                    disabled={uploading}
                    className="p-1.5 text-slate-400 hover:text-rose-600 transition cursor-pointer"
                    title="Remove file"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-2 flex items-center justify-between border-t border-slate-200">
            <p className="text-[11px] text-slate-500">
              Each document will be associated with its identified company and indexed in FAISS.
            </p>
            <button
              onClick={handleUploadStaged}
              disabled={uploading}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold shadow-xs transition flex items-center space-x-1.5 cursor-pointer"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Processing & Indexing...</span>
                </>
              ) : (
                <>
                  <span>Upload & Index Document{stagedFiles.length > 1 ? "s" : ""}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {uploadError && (
        <div className="mt-3 p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{uploadError}</span>
        </div>
      )}

      {uploadSuccessMsg && (
        <div className="mt-3 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{uploadSuccessMsg}</span>
        </div>
      )}
    </div>
  );
};
