import React, { useState, useEffect } from "react";
import { 
  FileText, 
  RotateCw, 
  Copy, 
  Check, 
  ShieldCheck,
  TrendingUp,
  DollarSign,
  PieChart,
  Layers,
  Printer,
  ChevronDown
} from "lucide-react";
import type { GeneratedReportResponse, DocumentItem } from "../types";
import { listDocuments, generateReport, getReport } from "../services/api";

interface Props {
  sessionId: string;
}

export const ReportView: React.FC<Props> = ({ sessionId }) => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [report, setReport] = useState<GeneratedReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const docs = await listDocuments(sessionId);
        setDocuments(docs);
        if (docs.length > 0 && !selectedDocId) {
          setSelectedDocId(docs[0].id);
        }
      } catch (err) {
        console.error("Failed to load documents", err);
      }
    };
    fetchDocs();
  }, [sessionId]);

  const loadReport = async (docId: string, forceRegenerate = false) => {
    setLoading(true);
    try {
      if (forceRegenerate) {
        const generated = await generateReport(sessionId, docId);
        setReport(generated);
      } else {
        const existing = await getReport(sessionId, docId);
        setReport(existing);
      }
    } catch (err) {
      console.error("Failed to fetch report", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDocId) {
      loadReport(selectedDocId);
    }
  }, [selectedDocId]);

  const handleCopy = () => {
    if (!report) return;
    const text = `# ${report.title}\n\n## EXECUTIVE SUMMARY\n${report.executive_summary}\n\n## KEY FINANCIALS\n` +
      report.key_financials.map((k) => `- ${k.metric_name}: ${k.value !== null ? `${k.value} ${k.unit || ""}` : "Not Reported"} (Page ${k.source_page || "N/A"})`).join("\n") +
      `\n\n## SOURCES\n` +
      report.sources.map((s) => `- ${s.company_name} | Page ${s.source_page}: ${s.snippet || ""}`).join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  // Helper to extract top KPIs for presenter highlight grid
  const findMetric = (keywords: string[]) => {
    if (!report) return null;
    return report.key_financials.find(k => 
      keywords.some(kw => k.metric_name.toLowerCase().includes(kw))
    );
  };

  const revenueMetric = findMetric(["revenue", "sales"]);
  const operatingMarginMetric = findMetric(["operating margin", "operating profit margin"]);
  const netProfitMetric = findMetric(["net profit", "net income"]);
  const debtMetric = findMetric(["debt", "liabilities"]);

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Executive Control Bar */}
      <div className="p-4 rounded-2xl glass-panel flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center space-x-3 flex-1 min-w-0">
          <label className="text-xs text-slate-400 font-bold tracking-wider uppercase shrink-0">Filing:</label>
          <div className="relative flex-1 max-w-md">
            <select
              value={selectedDocId || ""}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="w-full appearance-none bg-slate-950/80 border border-white/[0.09] rounded-xl px-4 py-2 pr-9 text-xs text-slate-100 font-semibold focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 transition cursor-pointer"
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id} className="bg-slate-900 text-slate-100">
                  {d.company_name ? `${d.company_name} — ` : ""}{d.document_name}
                </option>
              ))}
            </select>
            <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-2.5 pointer-events-none" />
          </div>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          {report && (
            <>
              <button
                onClick={handleCopy}
                className="px-3.5 py-2 rounded-xl bg-slate-900/80 hover:bg-slate-800 text-slate-200 border border-white/[0.08] text-xs font-semibold transition flex items-center space-x-2 cursor-pointer shadow-sm"
                title="Copy markdown report"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                <span>{copied ? "Copied" : "Copy Briefing"}</span>
              </button>

              <button
                onClick={handlePrint}
                className="px-3.5 py-2 rounded-xl bg-slate-900/80 hover:bg-slate-800 text-slate-200 border border-white/[0.08] text-xs font-semibold transition flex items-center space-x-2 cursor-pointer shadow-sm"
                title="Print or export to PDF"
              >
                <Printer className="w-3.5 h-3.5 text-slate-400" />
                <span>Export PDF</span>
              </button>
            </>
          )}

          <button
            onClick={() => selectedDocId && loadReport(selectedDocId, true)}
            disabled={loading || !selectedDocId}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-40 text-white text-xs font-bold shadow-lg shadow-emerald-950/40 ring-1 ring-white/10 transition flex items-center space-x-2 cursor-pointer"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>{report ? "Re-Analyze" : "Generate Briefing"}</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-24 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
            <RotateCw className="w-6 h-6 animate-spin text-emerald-400" />
          </div>
          <span className="text-sm font-semibold text-slate-200">Synthesizing Executive Financial Intelligence...</span>
          <p className="text-xs text-slate-500">Cross-verifying extracted statements against FAISS chunk embeddings</p>
        </div>
      ) : !report ? (
        <div className="py-20 text-center text-slate-500 border border-dashed border-white/[0.08] rounded-2xl p-8 bg-slate-950/30">
          <FileText className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="font-bold text-slate-200 text-base">No Executive Report Generated</p>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            Click "Generate Briefing" to compile audited statements, margin analysis, and source-grounded findings.
          </p>
        </div>
      ) : (
        /* Presenter Executive Briefing Document */
        <div className="space-y-6">
          {/* Top 4 KPI Presenter Ribbon */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
            {/* KPI 1: Revenue */}
            <div className="p-4 rounded-2xl glass-card border-white/[0.07] relative overflow-hidden group">
              <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                <span className="font-semibold uppercase tracking-wider text-slate-400">Total Revenue</span>
                <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div className="text-xl font-extrabold text-white font-mono tracking-tight">
                {revenueMetric && revenueMetric.value !== null ? (
                  <span>
                    {typeof revenueMetric.value === "number" ? revenueMetric.value.toLocaleString() : revenueMetric.value}
                    <span className="text-xs text-emerald-400 ml-1 font-sans">{revenueMetric.unit || ""}</span>
                  </span>
                ) : (
                  <span className="text-slate-500 text-sm italic font-sans">Not Reported</span>
                )}
              </div>
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.05] text-[10px] text-slate-400">
                <span>{revenueMetric?.fiscal_year || "Fiscal Period"}</span>
                {revenueMetric?.source_page && (
                  <span className="px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-300 font-mono text-[9px] border border-emerald-500/20">
                    Page {revenueMetric.source_page}
                  </span>
                )}
              </div>
            </div>

            {/* KPI 2: Operating Margin */}
            <div className="p-4 rounded-2xl glass-card border-white/[0.07] relative overflow-hidden group">
              <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                <span className="font-semibold uppercase tracking-wider text-slate-400">Operating Margin</span>
                <TrendingUp className="w-3.5 h-3.5 text-sky-400" />
              </div>
              <div className="text-xl font-extrabold text-white font-mono tracking-tight">
                {operatingMarginMetric && operatingMarginMetric.value !== null ? (
                  <span>
                    {operatingMarginMetric.value}
                    <span className="text-xs text-sky-400 ml-1 font-sans">{operatingMarginMetric.unit || "%"}</span>
                  </span>
                ) : (
                  <span className="text-slate-500 text-sm italic font-sans">Not Reported</span>
                )}
              </div>
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.05] text-[10px] text-slate-400">
                <span>Operating Stance</span>
                {operatingMarginMetric?.source_page && (
                  <span className="px-1.5 py-0.2 rounded bg-sky-500/10 text-sky-300 font-mono text-[9px] border border-sky-500/20">
                    Page {operatingMarginMetric.source_page}
                  </span>
                )}
              </div>
            </div>

            {/* KPI 3: Net Profit */}
            <div className="p-4 rounded-2xl glass-card border-white/[0.07] relative overflow-hidden group">
              <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                <span className="font-semibold uppercase tracking-wider text-slate-400">Net Profit</span>
                <PieChart className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              <div className="text-xl font-extrabold text-white font-mono tracking-tight">
                {netProfitMetric && netProfitMetric.value !== null ? (
                  <span>
                    {typeof netProfitMetric.value === "number" ? netProfitMetric.value.toLocaleString() : netProfitMetric.value}
                    <span className="text-xs text-indigo-400 ml-1 font-sans">{netProfitMetric.unit || ""}</span>
                  </span>
                ) : (
                  <span className="text-slate-500 text-sm italic font-sans">Not Reported</span>
                )}
              </div>
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.05] text-[10px] text-slate-400">
                <span>Net Bottom-Line</span>
                {netProfitMetric?.source_page && (
                  <span className="px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-300 font-mono text-[9px] border border-indigo-500/20">
                    Page {netProfitMetric.source_page}
                  </span>
                )}
              </div>
            </div>

            {/* KPI 4: Total Debt */}
            <div className="p-4 rounded-2xl glass-card border-white/[0.07] relative overflow-hidden group">
              <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                <span className="font-semibold uppercase tracking-wider text-slate-400">Total Debt</span>
                <Layers className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <div className="text-xl font-extrabold text-white font-mono tracking-tight">
                {debtMetric && debtMetric.value !== null ? (
                  <span>
                    {typeof debtMetric.value === "number" ? debtMetric.value.toLocaleString() : debtMetric.value}
                    <span className="text-xs text-amber-400 ml-1 font-sans">{debtMetric.unit || ""}</span>
                  </span>
                ) : (
                  <span className="text-slate-500 text-sm italic font-sans">Not Reported</span>
                )}
              </div>
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.05] text-[10px] text-slate-400">
                <span>Capital Structure</span>
                {debtMetric?.source_page && (
                  <span className="px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-300 font-mono text-[9px] border border-amber-500/20">
                    Page {debtMetric.source_page}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Main Executive Briefing Paper */}
          <div className="glass-panel rounded-3xl p-8 sm:p-10 space-y-8 shadow-2xl relative overflow-hidden border-white/[0.09]">
            {/* Background Watermark Stamp */}
            <div className="absolute right-6 top-6 pointer-events-none opacity-5 select-none font-mono text-7xl font-black text-white rotate-12">
              AUDITED
            </div>

            {/* Deck Header */}
            <div className="border-b border-white/[0.08] pb-6">
              <div className="flex items-center space-x-2 text-[10px] uppercase font-bold tracking-widest text-emerald-400 mb-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Audited Institutional Financial Intelligence Briefing</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
                {report.title}
              </h2>
              <div className="text-xs text-slate-400 mt-2 flex items-center space-x-3 flex-wrap">
                <span className="font-semibold text-slate-200">{report.company_name}</span>
                <span>•</span>
                <span className="px-2 py-0.5 rounded bg-white/[0.05] border border-white/[0.08] text-[11px]">
                  SEC Filing / Statutory Report
                </span>
                <span>•</span>
                <span className="text-slate-400">Compiled {new Date(report.created_at).toLocaleDateString()}</span>
              </div>
            </div>

            {/* 1. Executive Summary */}
            <div className="space-y-3">
              <div className="flex items-center space-x-2 text-xs font-bold tracking-wider text-slate-200 uppercase">
                <div className="w-1.5 h-4 rounded-full bg-emerald-400"></div>
                <span>Executive Summary & Takeaways</span>
              </div>
              <div className="p-6 rounded-2xl bg-slate-950/60 border border-white/[0.06] text-xs text-slate-200 leading-relaxed font-sans shadow-inner whitespace-pre-wrap">
                {report.executive_summary}
              </div>
            </div>

            {/* 2. Key Financial Indicators Table */}
            <div className="space-y-3">
              <div className="flex items-center space-x-2 text-xs font-bold tracking-wider text-slate-200 uppercase">
                <div className="w-1.5 h-4 rounded-full bg-sky-400"></div>
                <span>Verified Financial Statements Breakdown</span>
              </div>

              <div className="rounded-2xl border border-white/[0.08] overflow-hidden bg-slate-950/70 shadow-lg">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-[#0B0F19] text-slate-400 uppercase text-[10px] tracking-wider border-b border-white/[0.08]">
                    <tr>
                      <th className="py-3 px-5 font-bold">Financial Metric</th>
                      <th className="py-3 px-5 font-bold">Reported Amount</th>
                      <th className="py-3 px-5 font-bold">Fiscal Period</th>
                      <th className="py-3 px-5 font-bold text-right">Source Filing Reference</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {report.key_financials.map((k, idx) => (
                      <tr key={idx} className="hover:bg-white/[0.03] transition-colors">
                        <td className="py-3 px-5 font-semibold text-slate-100 flex items-center space-x-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400/60"></span>
                          <span>{k.metric_name}</span>
                        </td>
                        <td className="py-3 px-5 font-mono font-bold text-sm">
                          {k.value !== null && k.value !== undefined ? (
                            <span className="text-emerald-300">
                              {typeof k.value === "number" ? k.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : k.value}
                              {k.unit ? <span className="text-xs text-slate-400 ml-1 font-sans">{k.unit}</span> : ""}
                            </span>
                          ) : (
                            <span className="text-slate-500 italic text-xs font-sans">Not Reported</span>
                          )}
                        </td>
                        <td className="py-3 px-5 text-slate-400 font-mono text-[11px]">{k.fiscal_year || "—"}</td>
                        <td className="py-3 px-5 text-right">
                          {k.source_page ? (
                            <span className="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono text-[10px] inline-flex items-center space-x-1">
                              <span>Page {k.source_page}</span>
                            </span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 3. Verified Audit Trail & Sources */}
            <div className="space-y-3">
              <div className="flex items-center space-x-2 text-xs font-bold tracking-wider text-slate-200 uppercase">
                <div className="w-1.5 h-4 rounded-full bg-indigo-400"></div>
                <span>Filing Citations & Audit Provenance</span>
              </div>

              <div className="p-5 rounded-2xl bg-slate-950/60 border border-white/[0.06] space-y-2">
                {report.sources && report.sources.length > 0 ? (
                  report.sources.map((s, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs py-2 border-b border-white/[0.04] last:border-0">
                      <div className="flex items-center space-x-2.5 truncate max-w-md">
                        <span className="font-bold text-slate-200 shrink-0">{s.company_name || report.company_name}</span>
                        <span className="text-slate-400 truncate italic">"{s.snippet || "Audited statement snippet"}"</span>
                      </div>
                      {s.source_page && (
                        <span className="px-2 py-0.5 rounded bg-white/[0.05] text-slate-300 font-mono text-[10px] border border-white/[0.08] shrink-0">
                          Filing Page {s.source_page}
                        </span>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-500 italic">No external citations found.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
