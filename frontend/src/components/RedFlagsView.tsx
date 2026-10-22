import React, { useState, useEffect, useMemo } from "react";
import { 
  AlertTriangle, 
  CheckCircle2, 
  HelpCircle, 
  Building, 
  RotateCw, 
  ExternalLink,
  Search,
  ShieldCheck,
  ChevronDown,
  ChevronRight,
  Sparkles,
  ArrowRight
} from "lucide-react";
import type { RedFlagItem } from "../types";
import { listSessionRedFlags, triggerRedFlagAnalysis } from "../services/api";

interface Props {
  sessionId: string;
  onSelectDoc?: (docId: string) => void;
  onNavigateNext?: () => void;
}

export const RedFlagsView: React.FC<Props> = ({ sessionId, onSelectDoc, onNavigateNext }) => {
  const [flags, setFlags] = useState<RedFlagItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzingDocId, setAnalyzingDocId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedCompanyFilter, setSelectedCompanyFilter] = useState<string>("ALL");
  const [collapsedCompanies, setCollapsedCompanies] = useState<Record<string, boolean>>({});

  const fetchFlags = async () => {
    try {
      setLoading(true);
      const data = await listSessionRedFlags(sessionId);
      setFlags(data);
    } catch (err) {
      console.error("Failed to load red flags", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFlags();
  }, [sessionId]);

  const handleReanalyze = async (docId: string) => {
    setAnalyzingDocId(docId);
    try {
      await triggerRedFlagAnalysis(sessionId, docId);
      await fetchFlags();
    } catch (err) {
      console.error("Failed to analyze red flags", err);
    } finally {
      setAnalyzingDocId(null);
    }
  };

  const toggleCompanyCollapse = (compName: string) => {
    setCollapsedCompanies((prev) => ({
      ...prev,
      [compName]: !prev[compName]
    }));
  };

  // Group all flags by company_name
  const companyGroups = useMemo(() => {
    const groups: Record<
      string, 
      { 
        companyName: string; 
        documentId: string; 
        flags: RedFlagItem[];
        flaggedCount: number;
        cleanCount: number;
        insufficientCount: number;
        hasHighSeverity: boolean;
      }
    > = {};

    flags.forEach((f) => {
      const comp = f.company_name?.trim() || "Unassigned Company";
      if (!groups[comp]) {
        groups[comp] = {
          companyName: comp,
          documentId: f.document_id,
          flags: [],
          flaggedCount: 0,
          cleanCount: 0,
          insufficientCount: 0,
          hasHighSeverity: false
        };
      }
      groups[comp].flags.push(f);
      if (f.status === "FLAGGED") {
        groups[comp].flaggedCount += 1;
        if (f.severity === "HIGH") groups[comp].hasHighSeverity = true;
      } else if (f.status === "CLEAN") {
        groups[comp].cleanCount += 1;
      } else {
        groups[comp].insufficientCount += 1;
      }
    });

    return groups;
  }, [flags]);

  const companyNames = Object.keys(companyGroups).sort();

  // Filter flags based on search, severity, status, and company
  const filteredCompanyGroups = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    const result: Record<string, typeof companyGroups[string]> = {};

    companyNames.forEach((comp) => {
      if (selectedCompanyFilter !== "ALL" && comp !== selectedCompanyFilter) {
        return;
      }

      const compData = companyGroups[comp];
      const matchedFlags = compData.flags.filter((f) => {
        const matchesSearch = 
          !q ||
          f.title.toLowerCase().includes(q) ||
          f.description.toLowerCase().includes(q) ||
          (f.company_name || "").toLowerCase().includes(q) ||
          f.explanation.toLowerCase().includes(q);

        const matchesSeverity = severityFilter === "ALL" || f.severity === severityFilter;
        const matchesStatus = statusFilter === "ALL" || f.status === statusFilter;

        return matchesSearch && matchesSeverity && matchesStatus;
      });

      if (matchedFlags.length > 0 || !q) {
        result[comp] = {
          ...compData,
          flags: matchedFlags
        };
      }
    });

    return result;
  }, [companyGroups, companyNames, searchQuery, severityFilter, statusFilter, selectedCompanyFilter]);

  const flaggedTotal = flags.filter((f) => f.status === "FLAGGED").length;
  const cleanTotal = flags.filter((f) => f.status === "CLEAN").length;
  const insufficientTotal = flags.filter((f) => f.status === "INSUFFICIENT_EVIDENCE").length;

  const renderSeverityBadge = (severity: string) => {
    switch (severity) {
      case "HIGH":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 font-mono">HIGH RISK</span>;
      case "MEDIUM":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono">MEDIUM</span>;
      case "LOW":
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-sky-500/20 text-sky-300 border border-sky-500/40 font-mono">LOW</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700 font-mono">INFO</span>;
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "FLAGGED":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            <span>Flagged Risk</span>
          </span>
        );
      case "CLEAN":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Clean Baseline</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-white/[0.08]">
            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
            <span>Insufficient Evidence</span>
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16 font-sans">
      {/* Header Banner - Identifying Agent Name & Purpose */}
      <div className="p-5 rounded-3xl glass-panel border-white/[0.08] flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center space-x-3.5">
          <div className="p-2.5 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 shadow-md">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded-md bg-rose-500/15 text-rose-300 border border-rose-500/30 text-[10px] font-bold font-mono">
                Red Flag Agent
              </span>
              <span className="text-xs text-slate-400 font-medium">Systematic Financial Risk Audit</span>
            </div>
            <h2 className="text-base sm:text-lg font-extrabold text-white tracking-tight mt-0.5">
              Company-Wise Financial Risk Radar
            </h2>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed mt-0.5">
              Automated anomaly detection auditing 7 risk vectors per company: rising leverage, margin compression, profit volatility, cash flow divergence, and auditor qualifications.
            </p>
          </div>
        </div>

        {onNavigateNext && (
          <button
            onClick={onNavigateNext}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white text-xs font-bold transition flex items-center space-x-2 shrink-0 cursor-pointer shadow-md"
          >
            <span>Proceed to Step 5: Research & Compare</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* KPI Stats Across All Companies */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        <div className="p-4 rounded-2xl glass-card border-white/[0.07]">
          <span className="text-[10px] text-slate-400 uppercase tracking-widest block font-bold mb-1">Indexed Companies</span>
          <span className="text-2xl font-black text-white font-mono">{companyNames.length}</span>
        </div>
        <div className="p-4 rounded-2xl glass-card border-rose-500/25 bg-rose-950/10 shadow-[0_4px_20px_-4px_rgba(244,63,94,0.1)]">
          <span className="text-[10px] text-rose-400 uppercase tracking-widest block font-bold mb-1">Flagged Anomalies</span>
          <span className="text-2xl font-black text-rose-300 font-mono">{flaggedTotal}</span>
        </div>
        <div className="p-4 rounded-2xl glass-card border-emerald-500/25 bg-emerald-950/10 shadow-[0_4px_20px_-4px_rgba(16,185,129,0.1)]">
          <span className="text-[10px] text-emerald-400 uppercase tracking-widest block font-bold mb-1">Clean Baseline Checks</span>
          <span className="text-2xl font-black text-emerald-300 font-mono">{cleanTotal}</span>
        </div>
        <div className="p-4 rounded-2xl glass-card border-white/[0.07]">
          <span className="text-[10px] text-slate-400 uppercase tracking-widest block font-bold mb-1">Data Gaps / Neutral</span>
          <span className="text-2xl font-black text-slate-300 font-mono">{insufficientTotal}</span>
        </div>
      </div>

      {/* Company Selector Filter Pills */}
      <div className="p-3.5 rounded-2xl glass-panel space-y-2.5">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold text-slate-200 flex items-center space-x-1.5">
            <Building className="w-3.5 h-3.5 text-blue-400" />
            <span>Select Company Risk Dossier:</span>
          </span>
          <span>{companyNames.length} {companyNames.length === 1 ? "Company" : "Companies"} in Session</span>
        </div>

        <div className="flex items-center space-x-2 overflow-x-auto pb-1">
          <button
            onClick={() => setSelectedCompanyFilter("ALL")}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer whitespace-nowrap ${
              selectedCompanyFilter === "ALL"
                ? "bg-slate-100 text-slate-950 shadow-md font-extrabold"
                : "bg-slate-900/90 text-slate-400 hover:text-white border border-white/[0.08]"
            }`}
          >
            All Companies ({companyNames.length})
          </button>

          {companyNames.map((comp) => {
            const data = companyGroups[comp];
            const isSelected = selectedCompanyFilter === comp;
            const hasFlags = data.flaggedCount > 0;

            return (
              <button
                key={comp}
                onClick={() => setSelectedCompanyFilter(comp)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer whitespace-nowrap flex items-center space-x-2 border ${
                  isSelected
                    ? "bg-rose-500/20 text-rose-200 border-rose-500/50 shadow-md"
                    : "bg-slate-900/90 text-slate-400 hover:text-slate-200 border-white/[0.08]"
                }`}
              >
                <span>{comp}</span>
                {hasFlags ? (
                  <span className="px-1.5 py-0.2 rounded-full bg-rose-500/30 text-rose-300 text-[10px] font-mono font-bold">
                    {data.flaggedCount} Flagged
                  </span>
                ) : (
                  <span className="px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-mono">
                    Clean
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Search and Severity Filter Bar */}
      <div className="p-4 rounded-2xl glass-panel flex flex-col sm:flex-row items-center justify-between gap-3 shadow-lg">
        <div className="relative flex-1 w-full sm:w-80">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search risk checks, criteria, keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950/80 border border-white/[0.08] rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-rose-500/50 focus:ring-1 focus:ring-rose-500/20 transition font-sans"
          />
        </div>

        <div className="flex items-center space-x-2 flex-wrap w-full sm:w-auto justify-end">
          <div className="flex items-center space-x-1 bg-slate-950/70 border border-white/[0.07] rounded-xl p-1 text-xs">
            {["ALL", "FLAGGED", "CLEAN", "INSUFFICIENT_EVIDENCE"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 rounded-lg text-[10px] font-bold transition cursor-pointer ${
                  statusFilter === st
                    ? "bg-rose-500/20 text-rose-300 border border-rose-500/30 shadow-xs"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {st === "INSUFFICIENT_EVIDENCE" ? "Insufficient" : st}
              </button>
            ))}
          </div>

          <div className="flex items-center space-x-1 bg-slate-950/70 border border-white/[0.07] rounded-xl p-1 text-xs">
            {["ALL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition cursor-pointer ${
                  severityFilter === sev
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-xs"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Company-Wise Risk Sections */}
      {loading ? (
        <div className="py-20 text-center text-slate-500 flex flex-col items-center space-y-3">
          <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
            <RotateCw className="w-5 h-5 animate-spin text-rose-400" />
          </div>
          <span className="text-xs font-semibold text-slate-300">Auditing filings for company-wise financial risks...</span>
        </div>
      ) : Object.keys(filteredCompanyGroups).length === 0 ? (
        <div className="py-16 text-center text-slate-500 border border-dashed border-white/[0.08] rounded-2xl p-8 bg-slate-950/30">
          <ShieldCheck className="w-10 h-10 text-emerald-500/60 mx-auto mb-2" />
          <p className="font-bold text-slate-200 text-sm">No Risk Findings for this Filter</p>
          <p className="text-xs text-slate-400 mt-1">Audit opinions confirmed clean or matching criteria satisfied.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(filteredCompanyGroups).map(([compName, compData]) => {
            const isCollapsed = !!collapsedCompanies[compName];
            const isAnalyzing = analyzingDocId === compData.documentId;
            const hasHighRisk = compData.hasHighSeverity;

            return (
              <section 
                key={compName} 
                className="rounded-3xl border border-white/[0.09] bg-gradient-to-b from-[#0B0E17] to-[#07090F] overflow-hidden shadow-2xl"
              >
                {/* Company Risk Banner Header */}
                <div 
                  onClick={() => toggleCompanyCollapse(compName)}
                  className="p-5 sm:p-6 border-b border-white/[0.06] bg-slate-950/60 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer hover:bg-slate-900/40 transition select-none"
                >
                  <div className="flex items-center space-x-3.5">
                    <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 shrink-0">
                      <Building className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2.5 flex-wrap">
                        <h3 className="text-base font-bold text-white tracking-tight">
                          {compName}
                        </h3>
                        {compData.flaggedCount > 0 ? (
                          <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                            hasHighRisk 
                              ? "bg-rose-500/20 text-rose-300 border-rose-500/40" 
                              : "bg-amber-500/20 text-amber-300 border-amber-500/40"
                          }`}>
                            {hasHighRisk ? "CRITICAL / HIGH RISK" : "MODERATE RISK"}
                          </span>
                        ) : (
                          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                            CLEAN BASELINE
                          </span>
                        )}
                      </div>
                      <div className="flex items-center space-x-3 text-xs text-slate-400 mt-1">
                        <span className="text-rose-400 font-semibold">{compData.flaggedCount} Flagged</span>
                        <span>•</span>
                        <span className="text-emerald-400 font-semibold">{compData.cleanCount} Clean Baseline</span>
                        <span>•</span>
                        <span>{compData.insufficientCount} Data Gaps</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 shrink-0" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => handleReanalyze(compData.documentId)}
                      disabled={isAnalyzing}
                      className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/[0.08] text-xs font-medium transition flex items-center space-x-1.5 cursor-pointer"
                      title="Re-run Red Flag Agent for this Company"
                    >
                      <RotateCw className={`w-3.5 h-3.5 ${isAnalyzing ? "animate-spin text-rose-400" : ""}`} />
                      <span>{isAnalyzing ? "Analyzing..." : "Re-Scan Filing"}</span>
                    </button>

                    <button
                      onClick={() => toggleCompanyCollapse(compName)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-white transition cursor-pointer"
                    >
                      {isCollapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronDown className="w-5 h-5 text-slate-300" />}
                    </button>
                  </div>
                </div>

                {/* Company Risk Checks Body */}
                {!isCollapsed && (
                  <div className="p-5 sm:p-6 space-y-4">
                    {compData.flags.length === 0 ? (
                      <p className="text-xs text-slate-500 italic py-4 text-center">
                        No checks match the current search or severity filter for {compName}.
                      </p>
                    ) : (
                      compData.flags.map((flag) => {
                        const isFlagged = flag.status === "FLAGGED";

                        return (
                          <div
                            key={flag.id}
                            className={`p-5 rounded-2xl border transition-all duration-200 shadow-md ${
                              isFlagged
                                ? "glass-panel border-rose-500/30 hover:border-rose-500/50 bg-gradient-to-r from-rose-950/20 via-slate-900/90 to-slate-900/70"
                                : flag.status === "CLEAN"
                                ? "glass-panel border-white/[0.07] hover:border-emerald-500/30"
                                : "glass-card border-white/[0.05] opacity-80"
                            }`}
                          >
                            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-2.5">
                              <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                                {renderSeverityBadge(flag.severity)}
                                {renderStatusBadge(flag.status)}
                                {flag.fiscal_period && (
                                  <span className="text-[11px] text-slate-400 font-mono">
                                    Period: {flag.fiscal_period}
                                  </span>
                                )}
                              </div>

                              {flag.source_page && onSelectDoc && (
                                <button
                                  onClick={() => onSelectDoc(flag.document_id)}
                                  className="px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 transition text-xs font-semibold flex items-center space-x-1.5 cursor-pointer shrink-0"
                                  title="Jump to source page in Document Inspector"
                                >
                                  <span>Filing Page {flag.source_page}</span>
                                  <ExternalLink className="w-3 h-3" />
                                </button>
                              )}
                            </div>

                            <h4 className="text-sm font-bold text-white mb-1">{flag.title}</h4>
                            <p className="text-xs text-slate-300 leading-relaxed mb-3 font-sans">{flag.description}</p>

                            {/* Supporting Metrics */}
                            {flag.supporting_metrics && flag.supporting_metrics.length > 0 && (
                              <div className="flex flex-wrap gap-2 mb-3">
                                {flag.supporting_metrics.map((m, idx) => (
                                  <span
                                    key={idx}
                                    className="px-2.5 py-1 rounded-lg bg-slate-950/80 border border-white/[0.08] text-[11px] font-mono text-emerald-300"
                                  >
                                    {m}
                                  </span>
                                ))}
                              </div>
                            )}

                            {/* Evidence snippet */}
                            {flag.evidence_text && (
                              <div className="p-3 bg-slate-950/70 border border-white/[0.06] rounded-xl text-xs text-slate-300 font-sans italic mb-3">
                                "{flag.evidence_text}"
                              </div>
                            )}

                            <div className="pt-2 border-t border-white/[0.05] flex items-center justify-between text-[11px] text-slate-400">
                              <span>{flag.explanation}</span>
                              {flag.source_page && <span className="font-mono text-[10px]">Verified Source: Page {flag.source_page}</span>}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </section>
            );
          })}
        </div>
      )}

      {/* Order-Wise Next Step Banner */}
      {flags.length > 0 && onNavigateNext && (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-950/30 via-slate-900/80 to-slate-900/50 border border-emerald-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-6 shadow-xl">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-white flex items-center space-x-2">
                <span>Step 03 Complete: Company Risk Radars Audited</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Research Agent Ready
                </span>
              </h4>
              <p className="text-[11px] text-slate-400">
                Engage the autonomous Research Agent in multi-agent conversational RAG across all company filings.
              </p>
            </div>
          </div>
          <button
            onClick={onNavigateNext}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-lg shadow-emerald-950/50 flex items-center justify-center space-x-2 cursor-pointer transition shrink-0"
          >
            <span>Proceed to Step 04: Research / Chat</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};
