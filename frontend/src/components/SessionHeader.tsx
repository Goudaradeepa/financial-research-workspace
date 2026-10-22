import React from "react";
import { 
  Building2, 
  FileText, 
  Edit3,
  AlertTriangle,
  MessageSquare,
  BarChart3,
  FileSpreadsheet
} from "lucide-react";
import type { ResearchSession } from "../types";

export type WorkspaceTab = "documents" | "red_flags" | "chat" | "comparison" | "reports";

interface Props {
  session: ResearchSession;
  activeTab: WorkspaceTab;
  onTabChange: (tab: WorkspaceTab) => void;
  onRename?: () => void;
  currentUser?: any;
  onLogout?: () => void;
}

export const SessionHeader: React.FC<Props> = ({ 
  session, 
  activeTab,
  onTabChange,
  onRename
}) => {
  const tabs = [
    {
      id: "documents" as WorkspaceTab,
      label: "Documents & Files",
      badge: "Doc & Extraction Agents",
      icon: FileText
    },
    {
      id: "red_flags" as WorkspaceTab,
      label: "Risk Radar",
      badge: "Red Flag Agent",
      icon: AlertTriangle
    },
    {
      id: "chat" as WorkspaceTab,
      label: "Research / Chat",
      badge: "Research Agent (RAG)",
      icon: MessageSquare
    },
    {
      id: "comparison" as WorkspaceTab,
      label: "Comparison Matrix",
      badge: "Comparison Agent",
      icon: BarChart3
    },
    {
      id: "reports" as WorkspaceTab,
      label: "Executive Reports",
      badge: "Report Agent",
      icon: FileSpreadsheet
    }
  ];

  return (
    <header className="border-b border-slate-200 bg-white shrink-0 px-6 pt-4 pb-0">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3">
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
            {session.description || "Multi-agent research session for financial filing ingestion, risk radar, comparative analysis, and report synthesis."}
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

      {/* Modern Light Theme Agent Workspace Navigation Tabs */}
      <nav className="flex space-x-1 overflow-x-auto border-t border-slate-100 pt-1 -mb-px">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`px-3.5 py-2.5 text-xs font-medium border-b-2 flex items-center space-x-2 transition cursor-pointer shrink-0 ${
                isActive
                  ? "border-blue-600 text-blue-600 font-semibold bg-blue-50/40"
                  : "border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300"
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? "text-blue-600" : "text-slate-400"}`} />
              <span>{tab.label}</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                isActive 
                  ? "bg-blue-100 text-blue-700 font-normal" 
                  : "bg-slate-100 text-slate-500 font-normal"
              }`}>
                {tab.badge}
              </span>
            </button>
          );
        })}
      </nav>
    </header>
  );
};
