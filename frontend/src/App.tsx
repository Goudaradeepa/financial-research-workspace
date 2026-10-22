import React, { useState, useEffect } from "react";
import { Plus, Briefcase, ArrowRight } from "lucide-react";
import type { ResearchSession, DocumentItem, CreateSessionInput } from "./types";
import { listSessions, createSession, updateSession, deleteSession, deleteDocument } from "./services/api";
import { SessionSidebar } from "./components/SessionSidebar";
import { SessionHeader } from "./components/SessionHeader";
import { DocumentUpload } from "./components/DocumentUpload";
import { DocumentList } from "./components/DocumentList";
import { DocumentPreviewModal } from "./components/DocumentPreviewModal";
import { NewSessionModal } from "./components/NewSessionModal";
import { RenameSessionModal } from "./components/RenameSessionModal";
import { DeleteConfirmModal } from "./components/DeleteConfirmModal";

export const App: React.FC = () => {
  const [sessions, setSessions] = useState<ResearchSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Modals state
  const [isNewSessionModalOpen, setIsNewSessionModalOpen] = useState(false);
  const [sessionToRename, setSessionToRename] = useState<ResearchSession | null>(null);
  const [selectedDocIdForPreview, setSelectedDocIdForPreview] = useState<string | null>(null);

  // Delete confirmations
  const [sessionToDelete, setSessionToDelete] = useState<ResearchSession | null>(null);
  const [docToDelete, setDocToDelete] = useState<DocumentItem | null>(null);

  // Refresh trigger counter to sync doc list & sidebar aggregates
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const fetchSessions = async () => {
    try {
      const data = await listSessions();
      setSessions(data);

      // Restore active session or pick the latest
      if (data.length > 0) {
        const savedId = localStorage.getItem("active_financial_session_id");
        if (savedId && data.some((s) => s.id === savedId)) {
          setActiveSessionId(savedId);
        } else if (!activeSessionId) {
          setActiveSessionId(data[0].id);
        }
      } else {
        setActiveSessionId(null);
      }
    } catch (err) {
      console.error("Failed to list sessions", err);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [refreshTrigger]);

  const handleSelectSession = (id: string) => {
    setActiveSessionId(id);
    localStorage.setItem("active_financial_session_id", id);
  };

  const handleCreateSession = async (input: CreateSessionInput) => {
    const created = await createSession(input);
    await fetchSessions();
    handleSelectSession(created.id);
  };

  const handleRenameSession = async (sessionId: string, newName: string, newDescription?: string) => {
    await updateSession(sessionId, {
      name: newName,
      description: newDescription,
    });
    await fetchSessions();
  };

  const handleDeleteSession = async () => {
    if (!sessionToDelete) return;
    await deleteSession(sessionToDelete.id);
    setSessionToDelete(null);
    if (activeSessionId === sessionToDelete.id) {
      setActiveSessionId(null);
      localStorage.removeItem("active_financial_session_id");
    }
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleDeleteDocument = async () => {
    if (!docToDelete || !activeSessionId) return;
    await deleteDocument(activeSessionId, docToDelete.id);
    setDocToDelete(null);
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleUploadSuccess = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  const activeSession = sessions.find((s) => s.id === activeSessionId) || null;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 text-slate-900 font-sans">
      {/* Left Navigation Sidebar */}
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onOpenNewSessionModal={() => setIsNewSessionModalOpen(true)}
        onRenameSession={(s) => setSessionToRename(s)}
        onDeleteSession={(s) => setSessionToDelete(s)}
      />

      {/* Main Workspace */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-50/50">
        {activeSession ? (
          <div className="flex-1 flex flex-col h-full overflow-hidden">
            {/* Session Top Bar */}
            <SessionHeader 
              session={activeSession} 
              onRename={() => setSessionToRename(activeSession)}
            />

            {/* Main Content Area: PDF Upload & Document Table */}
            <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6">
              <div className="max-w-7xl mx-auto space-y-6">
                <DocumentUpload
                  sessionId={activeSession.id}
                  onUploadSuccess={handleUploadSuccess}
                />
                <DocumentList
                  sessionId={activeSession.id}
                  onSelectDoc={(id) => setSelectedDocIdForPreview(id)}
                  onDeleteDoc={(doc) => setDocToDelete(doc)}
                  refreshTrigger={refreshTrigger}
                />
              </div>
            </div>
          </div>
        ) : (
          /* Empty Workspace State */
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <div className="max-w-md w-full bg-white border border-slate-200/80 rounded-2xl p-8 shadow-sm space-y-6 text-center">
              <div className="w-14 h-14 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 mx-auto">
                <Briefcase className="w-7 h-7" />
              </div>

              <div className="space-y-2">
                <h2 className="text-xl font-bold tracking-tight text-slate-900">
                  Financial Research Workspace
                </h2>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Select a research session from the sidebar or initialize a new session to begin filing ingestion and automated metric extraction.
                </p>
              </div>

              <div>
                <button
                  onClick={() => setIsNewSessionModalOpen(true)}
                  className="w-full sm:w-auto px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg transition duration-150 shadow-xs inline-flex items-center justify-center space-x-2 cursor-pointer"
                >
                  <Plus className="w-4 h-4" />
                  <span>Create Research Session</span>
                  <ArrowRight className="w-3.5 h-3.5 opacity-70" />
                </button>
              </div>

              <div className="pt-5 border-t border-slate-100 grid grid-cols-3 gap-2 text-left">
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">01 Ingest</span>
                  <p className="text-[11px] text-slate-700 font-medium">Upload Annual Reports (PDF)</p>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">02 Index</span>
                  <p className="text-[11px] text-slate-700 font-medium">Document Agent FAISS Chunks</p>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">03 Extract</span>
                  <p className="text-[11px] text-slate-700 font-medium">Extraction Agent Grounded Metrics</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Create New Session Modal */}
      <NewSessionModal
        isOpen={isNewSessionModalOpen}
        onClose={() => setIsNewSessionModalOpen(false)}
        onSubmit={handleCreateSession}
      />

      {/* Rename Session Modal */}
      <RenameSessionModal
        session={sessionToRename}
        isOpen={!!sessionToRename}
        onClose={() => setSessionToRename(null)}
        onRename={handleRenameSession}
      />

      {/* Document Inspector & Preview Modal */}
      <DocumentPreviewModal
        sessionId={activeSessionId || ""}
        documentId={selectedDocIdForPreview}
        onClose={() => setSelectedDocIdForPreview(null)}
        onDocumentUpdated={() => setRefreshTrigger((prev) => prev + 1)}
      />

      {/* Delete Session Confirmation */}
      <DeleteConfirmModal
        isOpen={!!sessionToDelete}
        title="Delete Research Session"
        message="Are you sure you want to delete this research session? All associated financial documents, extracts, and index chunks will be permanently removed."
        itemTitle={sessionToDelete?.name}
        onConfirm={handleDeleteSession}
        onClose={() => setSessionToDelete(null)}
      />

      {/* Delete Document Confirmation */}
      <DeleteConfirmModal
        isOpen={!!docToDelete}
        title="Delete Financial Document"
        message="Are you sure you want to delete this document from the current session?"
        itemTitle={docToDelete?.filename}
        onConfirm={handleDeleteDocument}
        onClose={() => setDocToDelete(null)}
      />
    </div>
  );
};

export default App;
