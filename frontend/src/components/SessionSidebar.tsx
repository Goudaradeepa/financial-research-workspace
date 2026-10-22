import React, { useState } from "react";
import { Plus, Search, Layers, FileText, Trash2, Edit3, ChevronRight, Activity, ShieldCheck } from "lucide-react";
import type { ResearchSession } from "../types";

interface Props {
  sessions: ResearchSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onOpenNewSessionModal: () => void;
  onRenameSession: (session: ResearchSession) => void;
  onDeleteSession: (session: ResearchSession) => void;
}

export const SessionSidebar: React.FC<Props> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onOpenNewSessionModal,
  onRenameSession,
  onDeleteSession,
}) => {
  const [searchTerm, setSearchTerm] = useState("");

  const filtered = sessions.filter((s) => {
    const query = searchTerm.toLowerCase();
    return (
      s.name.toLowerCase().includes(query) ||
      (s.ticker && s.ticker.toLowerCase().includes(query)) ||
      (s.description && s.description.toLowerCase().includes(query))
    );
  });

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, { 
        year: "numeric", 
        month: "short", 
        day: "numeric" 
      });
    } catch {
      return "";
    }
  };

  return (
    <aside className="w-72 border-r border-slate-200 bg-white flex flex-col h-full shrink-0 relative z-20 text-slate-900 select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-200/80 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center font-bold text-sm shadow-xs">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-xs font-bold tracking-tight text-slate-900 uppercase">
              Financial Research
            </h1>
            <p className="text-[11px] text-slate-500 font-normal">AI Analysis Workspace</p>
          </div>
        </div>
      </div>

      {/* Action Button: New Research */}
      <div className="p-3 border-b border-slate-100">
        <button
          onClick={onOpenNewSessionModal}
          className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs transition flex items-center justify-center space-x-1.5 shadow-xs cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>New Research</span>
        </button>
      </div>

      {/* Search Sessions */}
      <div className="px-3 py-2 border-b border-slate-100">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search sessions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
          />
        </div>
      </div>

      {/* Research Sessions List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        <div className="px-2 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
          Research Sessions
        </div>

        {filtered.length === 0 ? (
          <div className="py-10 px-3 text-center">
            <Layers className="w-7 h-7 text-slate-300 mx-auto mb-2" />
            <p className="text-xs text-slate-600 font-medium">No sessions found</p>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Create a new research session to begin.
            </p>
          </div>
        ) : (
          filtered.map((s) => {
            const isActive = s.id === activeSessionId;
            const docCount = s.document_count || 0;
            const docLabel = docCount === 1 ? "1 file" : `${docCount} files`;

            return (
              <div
                key={s.id}
                onClick={() => onSelectSession(s.id)}
                className={`group relative rounded-lg p-2.5 cursor-pointer transition border text-left ${
                  isActive
                    ? "bg-blue-50/70 border-blue-200 text-slate-900 shadow-xs"
                    : "bg-white hover:bg-slate-50/80 border-transparent hover:border-slate-200 text-slate-700"
                }`}
              >
                <div className="flex items-start justify-between gap-1.5">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-1.5 mb-1 flex-wrap">
                      {s.ticker && (
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200 shrink-0">
                          {s.ticker}
                        </span>
                      )}
                      <h3
                        className={`text-xs font-semibold leading-snug truncate ${
                          isActive ? "text-blue-950 font-bold" : "text-slate-800 group-hover:text-slate-900"
                        }`}
                        title={s.name}
                      >
                        {s.name}
                      </h3>
                    </div>

                    <div className="text-[11px] text-slate-500 flex items-center space-x-2">
                      <span className="flex items-center space-x-1">
                        <FileText className="w-3 h-3 text-slate-400" />
                        <span>{docLabel}</span>
                      </span>
                      <span>•</span>
                      <span>{formatDate(s.updated_at || s.created_at)}</span>
                    </div>
                  </div>

                  {/* Actions: Rename & Delete */}
                  <div className="flex items-center space-x-0.5 shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onRenameSession(s);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded transition cursor-pointer"
                      title="Rename Session"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(s);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition cursor-pointer"
                      title="Delete Session"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    {isActive && (
                      <ChevronRight className="w-3.5 h-3.5 text-blue-600 ml-0.5" />
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Clean Compact Footer */}
      <div className="p-3 border-t border-slate-200 bg-slate-50/60 text-[11px] text-slate-500 flex items-center justify-between">
        <span className="flex items-center space-x-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
          <span>Local Storage</span>
        </span>
        <span className="font-mono text-[10px] text-slate-400">{sessions.length} sessions</span>
      </div>
    </aside>
  );
};
