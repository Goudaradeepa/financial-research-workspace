import React, { useState, useEffect, useRef } from "react";
import { 
  Send, 
  Bot, 
  User, 
  Sparkles, 
  Loader2, 
  RotateCcw,
  HelpCircle,
  ArrowRight
} from "lucide-react";
import type { ChatMessage } from "../types";
import { sendChatMessage, getChatHistory } from "../services/api";

interface Props {
  sessionId: string;
  onNavigateNext?: () => void;
}

export const ResearchChatView: React.FC<Props> = ({ sessionId, onNavigateNext }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const defaultSuggestions = [
    "What was total revenue and operating margin in the latest fiscal year?",
    "What are the major detected financial red flags or auditor qualifications?",
    "Compare available companies on revenue, net profit, and debt."
  ];

  const fetchHistory = async () => {
    try {
      const history = await getChatHistory(sessionId);
      if (history.length > 0) {
        const loaded: ChatMessage[] = [];
        history.forEach((h: any) => {
          loaded.push({
            role: "user",
            content: h.query,
            timestamp: h.created_at
          });
          loaded.push({
            role: "assistant",
            content: h.answer,
            agent_used: h.agent_used,
            sources: h.sources,
            timestamp: h.created_at
          });
        });
        setMessages(loaded);
      } else {
        // Welcome message
        setMessages([
          {
            role: "assistant",
            content: "Welcome to the Conversational Financial Research Desk. Ask any financial question grounded strictly in your indexed filings.",
            agent_used: "Research Agent",
            suggested_queries: defaultSuggestions
          }
        ]);
      }
    } catch (err) {
      console.error("Failed to load chat history", err);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (queryText?: string) => {
    const q = (queryText || inputPrompt).trim();
    if (!q || loading) return;

    setInputPrompt("");
    const userMsg: ChatMessage = { role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await sendChatMessage(sessionId, q);
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: res.answer,
        agent_used: res.agent_used,
        intent: res.intent,
        sources: res.sources,
        suggested_queries: res.suggested_queries
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error retrieving financial answer: ${err.message || "Failed to process query."}`,
          agent_used: "Error"
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[75vh] glass-panel rounded-3xl overflow-hidden shadow-2xl border-white/[0.09] max-w-5xl mx-auto">
      {/* Chat Header */}
      <div className="px-6 py-4 border-b border-white/[0.06] bg-[#0A0D15]/80 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white flex items-center space-x-2">
              <span>Financial Intelligence Terminal</span>
              <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                LangGraph StateGraph
              </span>
              <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                LangChain LLM
              </span>
            </h3>
            <p className="text-[10px] text-slate-400">
              LangGraph multi-agent workflow: Supervisor Router → Research Agent → Red Flag Agent → Comparison Agent → LLM Synthesis.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {onNavigateNext && (
            <button
              onClick={onNavigateNext}
              className="px-3 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/30 text-xs font-semibold transition flex items-center space-x-1.5 cursor-pointer shadow-sm"
              title="Proceed to Step 05: Compare Companies"
            >
              <span>Step 05: Compare Companies</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            onClick={fetchHistory}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06] transition cursor-pointer"
            title="Reload chat history"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Message Thread */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 font-sans">
        {messages.map((msg, idx) => {
          const isUser = msg.role === "user";

          return (
            <div
              key={idx}
              className={`flex items-start space-x-3 ${isUser ? "flex-row-reverse space-x-reverse" : ""}`}
            >
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-xs shadow-md ${
                  isUser
                    ? "bg-gradient-to-br from-emerald-600 to-teal-700 text-white"
                    : "bg-slate-900 border border-white/[0.1] text-emerald-400"
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              <div
                className={`max-w-2xl rounded-2xl p-5 text-xs leading-relaxed shadow-lg ${
                  isUser
                    ? "bg-gradient-to-r from-emerald-600/90 to-teal-700/90 text-white rounded-tr-none ring-1 ring-white/10"
                    : "glass-card text-slate-200 rounded-tl-none border-white/[0.08]"
                }`}
              >
                {/* Agent Badge */}
                {!isUser && msg.agent_used && (
                  <div className="flex items-center space-x-2 mb-3 pb-2 border-b border-white/[0.06] text-[10px] text-slate-400">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="font-bold text-slate-200">{msg.agent_used}</span>
                    <span>•</span>
                    <span className="text-emerald-400 font-medium">Audited Filing Grounded</span>
                  </div>
                )}

                {/* Content formatted */}
                <div className="whitespace-pre-wrap font-sans text-xs space-y-1.5 text-slate-100">
                  {msg.content}
                </div>

                {/* Grounded Source Citations */}
                {!isUser && msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-white/[0.06] space-y-2">
                    <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                      Audited Filing Citations:
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {msg.sources.map((src, sIdx) => (
                        <div
                          key={sIdx}
                          className="px-2.5 py-1 rounded-lg bg-slate-950/80 border border-white/[0.08] text-[10px] text-slate-300 flex items-center space-x-2"
                          title={src.snippet || undefined}
                        >
                          {src.company_name && (
                            <span className="text-emerald-300 font-bold">{src.company_name}</span>
                          )}
                          {src.source_page && (
                            <span className="px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-300 font-mono text-[9px] border border-emerald-500/20">
                              Page {src.source_page}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Suggested Queries */}
                {!isUser && msg.suggested_queries && msg.suggested_queries.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-white/[0.06] flex flex-wrap gap-2">
                    {msg.suggested_queries.map((sq, sqIdx) => (
                      <button
                        key={sqIdx}
                        onClick={() => handleSend(sq)}
                        className="px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-emerald-500/15 border border-white/[0.08] hover:border-emerald-500/30 text-slate-300 hover:text-emerald-200 text-[10px] transition text-left cursor-pointer flex items-center space-x-1.5"
                      >
                        <HelpCircle className="w-3 h-3 text-emerald-400" />
                        <span>{sq}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 rounded-xl bg-slate-900 border border-white/[0.1] flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="glass-card rounded-2xl rounded-tl-none p-4 text-xs text-slate-400 flex items-center space-x-2.5">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span>Retrieving grounded findings from FAISS vector store and SQLite...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="p-4 border-t border-white/[0.06] bg-[#0A0D15]/90">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center space-x-2.5"
        >
          <input
            type="text"
            placeholder="Ask about revenue, profits, operating margins, debt, auditor opinions, or peer comparison..."
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            disabled={loading}
            className="flex-1 bg-slate-950/80 border border-white/[0.09] rounded-xl px-4 py-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition font-sans"
          />
          <button
            type="submit"
            disabled={!inputPrompt.trim() || loading}
            className="px-5 py-3 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-40 text-white text-xs font-bold shadow-lg shadow-emerald-950/50 ring-1 ring-white/10 transition flex items-center space-x-2 cursor-pointer shrink-0"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            <span>Ask</span>
          </button>
        </form>
      </div>
    </div>
  );
};
