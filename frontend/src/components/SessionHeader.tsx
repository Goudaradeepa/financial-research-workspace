import React from "react";
import { 
  Building2, 
  FileText, 
  Edit3
} from "lucide-react";
import type { ResearchSession } from "../types";

export type WorkspaceTab = "documents";

interface Props {
  session: ResearchSession;
  activeTab?: string;
  onTabChange?: (tab: any) => void;
  onRename?: () => void;
  currentUser?: any;
  onLogout?: () => void;
}

export const SessionHeader: React.FC<Props> = ({ 
  session, 
  onRename
}) => {
  return (
    <header className="border-b border-slate-200 bg-white shrink-0 px-6 py-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center space-x-2.5 flex-wrap">
            {session.ticker && (
              <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono text-xs font-semibold flex items-center space-x-1 shrink-0">
                <Building2 className="w-3.5 h-3.5 text-slate-500" />
                <span>{session.ticker}</span>
              </span>
            )}
            <h2 className="text-lg font-bold text-slate-900 truncate tracking-tight">
              {session.name}
            </h2>
            {onRename && (
              <button
                onClick={onRename}
                className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"
                title="Rename session"
              >
                <Edit3 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
            {session.description || "Research session for ingesting financial filings, indexing vector chunks, and extracting grounded metrics."}
          </p>
        </div>

        {/* Right side Document count badge */}
        <div className="flex items-center space-x-3 shrink-0">
          <div className="px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700 flex items-center space-x-2">
            <FileText className="w-3.5 h-3.5 text-slate-400" />
            <span>
              {session.document_count} {session.document_count === 1 ? "document" : "documents"} indexed
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
