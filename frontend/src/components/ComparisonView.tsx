import React, { useState, useEffect } from "react";
import { 
  BarChart3, 
  Building, 
  RotateCw, 
  ShieldCheck,
  Check,
  ArrowRightLeft,
  ArrowRight,
  FileCheck
} from "lucide-react";
import type { ComparisonResponse, DocumentItem } from "../types";
import { compareDocuments, listDocuments } from "../services/api";

interface Props {
  sessionId: string;
  onNavigateNext?: () => void;
}

export const ComparisonView: React.FC<Props> = ({ sessionId, onNavigateNext }) => {
  const [availableDocs, setAvailableDocs] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);

  // Fetch available documents in this session
  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const docs = await listDocuments(sessionId);
        setAvailableDocs(docs);
        // By default select all documents (or up to 4)
        if (docs.length >= 2) {
          setSelectedDocIds(docs.slice(0, 4).map((d) => d.id));
        } else if (docs.length === 1) {
          setSelectedDocIds([docs[0].id]);
        }
      } catch (err) {
        console.error("Failed to load documents for comparison", err);
      }
    };
    fetchDocs();
  }, [sessionId]);

  const runComparison = async (docIdsToCompare?: string[]) => {
    const ids = docIdsToCompare || selectedDocIds;
    if (ids.length === 0) return;

    try {
      setLoading(true);
      const res = await compareDocuments(sessionId, ids);
      setComparison(res);
    } catch (err) {
      console.error("Failed to execute comparison", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDocIds.length > 0) {
      runComparison();
    }
  }, [selectedDocIds]);

  const toggleDocSelection = (docId: string) => {
    setSelectedDocIds((prev) => {
      if (prev.includes(docId)) {
        return prev.filter((id) => id !== docId);
      } else {
        return [...prev, docId];
      }
    });
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Document Selector Bar */}
      <div className="p-5 rounded-2xl glass-panel flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
        <div>
          <h3 className="text-xs font-bold text-white flex items-center space-x-2 tracking-wide">
            <ArrowRightLeft className="w-4 h-4 text-indigo-400" />
            <span>Multi-Company Cross-Filing Matrix</span>
          </h3>
          <p className="text-[11px] text-slate-400 mt-1">
            Select 2 or more indexed company filings to generate a neutral, factual comparison matrix.
          </p>
        </div>

        {/* Checkbox pills */}
        <div className="flex flex-wrap gap-2 items-center">
          {availableDocs.map((doc) => {
            const isSelected = selectedDocIds.includes(doc.id);
            const compName = doc.company_name || doc.document_name;

            return (
              <button
                key={doc.id}
                onClick={() => toggleDocSelection(doc.id)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200 flex items-center space-x-2 cursor-pointer border ${
                  isSelected
                    ? "bg-indigo-500/15 border-indigo-400/50 text-indigo-200 shadow-md shadow-indigo-950/30"
                    : "bg-slate-950/60 border-white/[0.08] text-slate-400 hover:text-slate-200 hover:border-white/[0.15]"
                }`}
              >
                <div
                  className={`w-3.5 h-3.5 rounded flex items-center justify-center border text-[9px] ${
                    isSelected ? "bg-indigo-600 border-indigo-600 text-white" : "border-slate-600"
                  }`}
                >
                  {isSelected && <Check className="w-2.5 h-2.5" />}
                </div>
                <span className="truncate max-w-[160px] font-sans">{compName}</span>
              </button>
            );
          })}
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center text-slate-500 flex flex-col items-center justify-center space-y-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
            <RotateCw className="w-5 h-5 animate-spin text-indigo-400" />
          </div>
          <span className="text-xs font-semibold text-slate-300">Aligning statements and computing factual variances...</span>
        </div>
      ) : !comparison || comparison.companies.length === 0 ? (
        <div className="py-20 text-center text-slate-500 border border-dashed border-white/[0.08] rounded-2xl p-8 bg-slate-950/30">
          <BarChart3 className="w-10 h-10 text-slate-600 mx-auto mb-2" />
          <p className="font-bold text-slate-200 text-sm">Select At Least One Filing</p>
          <p className="text-xs text-slate-400 mt-1">Upload and select filings to generate comparative peer matrices.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Comparison Matrix Table */}
          <div className="glass-panel rounded-3xl overflow-hidden shadow-2xl border-white/[0.09]">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-[#0B0F19] text-slate-400 uppercase text-[10px] tracking-wider border-b border-white/[0.08]">
                  <tr>
                    <th className="py-3.5 px-5 font-bold min-w-[200px]">Financial Indicator</th>
                    {comparison.companies.map((c) => (
                      <th key={c} className="py-3.5 px-5 font-bold min-w-[170px]">
                        <div className="flex items-center space-x-2 text-white">
                          <Building className="w-3.5 h-3.5 text-indigo-400" />
                          <span className="truncate">{c}</span>
                        </div>
                      </th>
                    ))}
                    {comparison.companies.length === 2 && (
                      <th className="py-3.5 px-5 font-bold min-w-[190px] text-amber-300">Factual Delta / Note</th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] font-sans">
                  {comparison.metrics_table.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-3.5 px-5 font-semibold text-slate-100 flex items-center space-x-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-400/60"></span>
                        <span>{row.metric_name}</span>
                      </td>

                      {comparison.companies.map((c) => {
                        const item = row.company_values[c] || {};
                        const isAvail = item.status === "available";

                        return (
                          <td key={c} className="py-3.5 px-5">
                            {isAvail ? (
                              <div>
                                <div className="font-mono font-bold text-slate-100 text-sm">
                                  {typeof item.value === "number"
                                    ? item.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                                    : item.value}
                                  {item.unit ? <span className="text-xs text-slate-400 ml-1 font-sans">{item.unit}</span> : ""}
                                </div>
                                <div className="flex items-center space-x-2 text-[10px] text-slate-400 mt-1">
                                  {item.fiscal_year && <span className="font-mono text-slate-400">{item.fiscal_year}</span>}
                                  {item.source_page && (
                                    <span className="px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono text-[9px]">
                                      Page {item.source_page}
                                    </span>
                                  )}
                                </div>
                              </div>
                            ) : (
                              <span className="text-slate-500 italic text-xs font-sans">
                                Not Reported
                              </span>
                            )}
                          </td>
                        );
                      })}

                      {comparison.companies.length === 2 && (
                        <td className="py-3.5 px-5 text-xs text-slate-300">
                          {row.difference_note ? (
                            <span className="px-2.5 py-1 rounded-md bg-white/[0.04] border border-white/[0.06] text-amber-200 font-mono text-[11px] block">
                              {row.difference_note}
                            </span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Factual Executive Comparison Synthesis */}
          <div className="glass-panel rounded-2xl p-6 border-white/[0.08] space-y-2 shadow-xl">
            <h4 className="text-xs font-bold text-white flex items-center space-x-2 uppercase tracking-wider">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Comparative Synthesis (Objective & Factual)</span>
            </h4>
            <div className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-sans pt-1">
              {comparison.executive_comparison}
            </div>
          </div>

          {/* Order-Wise Next Step Banner */}
          {onNavigateNext && (
            <div className="p-4 rounded-2xl bg-gradient-to-r from-amber-950/30 via-slate-900/80 to-slate-900/50 border border-amber-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <FileCheck className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-white flex items-center space-x-2">
                    <span>Step 05 Complete: Cross-Company Benchmark Analyzed</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      Report Agent Ready
                    </span>
                  </h4>
                  <p className="text-[11px] text-slate-400">
                    Generate the final institutional-grade executive markdown dossier with full audit trail citations.
                  </p>
                </div>
              </div>
              <button
                onClick={onNavigateNext}
                className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white text-xs font-bold shadow-lg shadow-amber-950/50 flex items-center justify-center space-x-2 cursor-pointer transition shrink-0"
              >
                <span>Proceed to Step 06: Executive Dossier</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
