import os
import re
import json
import logging
import uuid
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from database import get_db_connection
from research_agent import decompose_question, answer_financial_research_query
from comparison_agent import compare_company_documents
from red_flag_agent import get_session_red_flags, analyze_red_flags

logger = logging.getLogger(__name__)

class FinancialAgentState(TypedDict):
    session_id: str
    query: str
    document_id: Optional[str]
    intent: str  # "research", "comparison", "red_flags", "clarification"
    sub_topics: List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]
    verified_metrics: List[Dict[str, Any]]
    findings: List[str]
    sources: List[Dict[str, Any]]
    final_answer: str
    agent_used: str
    suggested_queries: Optional[List[str]]

# 1. Supervisor / Intent Classifier Node
def supervisor_router_node(state: FinancialAgentState) -> Dict[str, Any]:
    """LangGraph Node: Classifies user financial query intent."""
    raw_query = state["query"].strip()
    lower_query = raw_query.lower()

    # Vague greetings
    vague_patterns = [r"^(hi|hello|hey|greetings|help|test|ping)$", r"^.{1,3}$"]
    if any(re.match(p, lower_query) for p in vague_patterns):
        return {
            "intent": "clarification",
            "agent_used": "LangGraph Supervisor",
            "final_answer": (
                "I am your Financial Research Assistant powered by LangGraph & LangChain. "
                "Please specify a financial inquiry, for example:\n\n"
                "- *\"What was the company's revenue and operating margin?\"*\n"
                "- *\"What are the major red flags or auditor qualifications?\"*\n"
                "- *\"Compare companies on revenue, profit, and debt.\"*"
            ),
            "sources": [],
            "suggested_queries": [
                "What was the company's revenue and operating margin?",
                "What are the major red flags?",
                "Compare companies on revenue, profit, and debt."
            ]
        }

    # Comparison intent
    comparison_keywords = [r"\b(compare|comparison|versus|vs\.?|side-by-side|between)\b"]
    if any(re.search(kw, lower_query) for kw in comparison_keywords):
        return {"intent": "comparison", "agent_used": "LangGraph Comparison Agent"}

    # Red flag intent
    risk_keywords = [r"\b(red flag|red flags|risk|risks|auditor|qualification|warning|warnings|default|debt risk)\b"]
    if any(re.search(kw, lower_query) for kw in risk_keywords):
        return {"intent": "red_flags", "agent_used": "LangGraph Red Flag Agent"}

    # Default to deep research
    return {"intent": "research", "agent_used": "LangGraph Research Agent"}

# 2. Research Agent Node
def research_agent_node(state: FinancialAgentState) -> Dict[str, Any]:
    """LangGraph Node: Decomposes query and performs FAISS dense vector retrieval."""
    res = answer_financial_research_query(
        session_id=state["session_id"],
        query=state["query"],
        document_id=state.get("document_id")
    )
    return {
        "findings": res.get("findings", []),
        "sources": res.get("sources", []),
        "final_answer": res.get("answer", ""),
        "agent_used": "LangGraph Research Agent"
    }

# 3. Red Flag Agent Node
def red_flag_agent_node(state: FinancialAgentState) -> Dict[str, Any]:
    """LangGraph Node: Analyzes financial risks & auditor qualifications."""
    session_id = state["session_id"]
    doc_id = state.get("document_id")

    if doc_id:
        flags = analyze_red_flags(doc_id)
    else:
        flags = get_session_red_flags(session_id)

    flagged_items = [f for f in flags if f.get("status") == "FLAGGED"]
    clean_items = [f for f in flags if f.get("status") == "CLEAN"]

    sources = []
    seen = set()
    for f in flags:
        p = f.get("source_page")
        d_id = f.get("document_id")
        if p and (d_id, p) not in seen:
            seen.add((d_id, p))
            sources.append({
                "company_name": f.get("company_name", ""),
                "document_name": "Audited Filing",
                "source_page": p,
                "source_chunk_id": f.get("source_chunk_id"),
                "snippet": f"{f.get('title')}: {f.get('explanation')}"
            })

    if flagged_items:
        lines = [f"### Detected Risk Warnings ({len(flagged_items)} items)\n"]
        for f in flagged_items:
            comp = f.get("company_name", "Company")
            p_str = f" (Page {f['source_page']})" if f.get("source_page") else ""
            lines.append(f"- **[{f['severity']}] {comp} - {f['title']}**: {f['description']}{p_str}")
        lines.append("\n*Source Citations: Verified against filing pages from indexed documents.*")
        answer_text = "\n".join(lines)
    else:
        answer_text = (
            f"### Financial Risk Assessment: Clean Baseline\n\n"
            f"No critical financial flags detected across {len(clean_items)} verified risk criteria. "
            f"Auditor reports reflect unqualified clean opinions with no going-concern warnings."
        )

    return {
        "findings": [answer_text],
        "sources": sources,
        "final_answer": answer_text,
        "agent_used": "LangGraph Red Flag Agent"
    }

# 4. Comparison Agent Node
def comparison_agent_node(state: FinancialAgentState) -> Dict[str, Any]:
    """LangGraph Node: Aligns multi-company metrics into a side-by-side matrix."""
    comp = compare_company_documents(
        session_id=state["session_id"],
        document_ids=[state["document_id"]] if state.get("document_id") else None
    )

    if not comp.get("companies"):
        return {
            "final_answer": "Insufficient evidence: At least one processed company filing is required to generate a comparison matrix.",
            "sources": [],
            "agent_used": "LangGraph Comparison Agent"
        }

    header = f"### Corporate Financial Comparison Matrix: {' vs '.join(comp['companies'])}\n\n"
    table_rows = ["| Financial Metric | " + " | ".join(comp["companies"]) + " | Variance / Difference |",
                  "| --- | " + " | ".join(["---"] * len(comp["companies"])) + " | --- |"]

    sources = []
    for r in comp.get("metrics_table", []):
        m_name = r["metric_name"]
        cols = []
        for c in comp["companies"]:
            val_info = r["company_values"].get(c, {})
            if val_info.get("status") == "available" and val_info.get("value") is not None:
                unit = f" {val_info.get('unit')}" if val_info.get("unit") else ""
                cols.append(f"{val_info['value']}{unit} (P.{val_info.get('source_page', 'N/A')})")
                if val_info.get("source_page"):
                    sources.append({
                        "company_name": c,
                        "document_name": "Financial Filing",
                        "source_page": val_info["source_page"],
                        "source_chunk_id": None,
                        "snippet": f"{m_name} = {val_info['value']}{unit}"
                    })
            else:
                cols.append("Not Reported")
        diff = r.get("difference_note", "—")
        table_rows.append(f"| **{m_name}** | " + " | ".join(cols) + f" | {diff} |")

    answer_text = header + "\n".join(table_rows) + f"\n\n**Executive Synthesis:**\n{comp.get('executive_comparison', '')}"
    return {
        "final_answer": answer_text,
        "sources": sources,
        "agent_used": "LangGraph Comparison Agent"
    }

# 5. LangChain LLM Synthesis Node (With zero-hallucination fallback)
def llm_synthesis_node(state: FinancialAgentState) -> Dict[str, Any]:
    """
    LangGraph Node: Uses LangChain ChatOpenAI / LLM to polish and synthesize findings.
    Strictly instructs LLM never to alter factual numbers or page citations.
    Falls back gracefully if LLM quota is unavailable.
    """
    draft_answer = state.get("final_answer", "")
    sources = state.get("sources", [])
    query = state.get("query", "")

    # If already formatted or clarification, preserve
    if state.get("intent") == "clarification" or not draft_answer:
        return state

    # Check if OpenAI API key is available and active
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key and not api_key.startswith("mock_"):
        try:
            llm = ChatOpenAI(
                model=os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini"),
                temperature=0.0,
                max_tokens=600,
                timeout=3,
                max_retries=0
            )

            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=(
                    "You are a Senior Financial Research Analyst in a LangGraph Multi-Agent system. "
                    "Your job is to format and present the verified financial findings clearly. "
                    "CRITICAL RULES:\n"
                    "1. NEVER invent, hallucinate, or alter financial numbers, dates, or metrics.\n"
                    "2. Preserve all filing source page references (e.g. Page 2, Page 3).\n"
                    "3. Present the findings with professional Wall Street executive clarity.\n"
                    "4. If evidence is insufficient, explicitly state that."
                )),
                HumanMessage(content=(
                    f"User Query: {query}\n\n"
                    f"Verified Grounded Findings from FAISS & Database:\n{draft_answer}\n\n"
                    "Format and synthesize this into a structured executive response with citations."
                ))
            ])

            chain = prompt | llm
            res = chain.invoke({})
            if res and res.content and len(res.content.strip()) > 20:
                return {
                    "final_answer": res.content.strip(),
                    "agent_used": f"{state.get('agent_used', 'Agent')} (LangChain LLM Synthesized)"
                }
        except Exception as e:
            logger.info(f"[LangGraph LLM Node] LLM call bypassed (quota/offline): {e}. Using grounded deterministic synthesis.")

    # Graceful fallback to verified draft answer
    return {
        "final_answer": draft_answer,
        "agent_used": state.get("agent_used", "LangGraph Agent")
    }

# 6. Conditional Edge Router
def route_next_node(state: FinancialAgentState) -> str:
    intent = state.get("intent", "research")
    if intent == "clarification":
        return END
    elif intent == "comparison":
        return "comparison_agent"
    elif intent == "red_flags":
        return "red_flag_agent"
    else:
        return "research_agent"

# 7. Build and Compile the LangGraph StateGraph
def build_financial_research_graph():
    builder = StateGraph(FinancialAgentState)

    # Add Nodes
    builder.add_node("supervisor_router", supervisor_router_node)
    builder.add_node("research_agent", research_agent_node)
    builder.add_node("red_flag_agent", red_flag_agent_node)
    builder.add_node("comparison_agent", comparison_agent_node)
    builder.add_node("llm_synthesis", llm_synthesis_node)

    # Add Edges
    builder.add_edge(START, "supervisor_router")

    # Conditional Routing from Supervisor Router
    builder.add_conditional_edges(
        "supervisor_router",
        route_next_node,
        {
            END: END,
            "research_agent": "research_agent",
            "red_flag_agent": "red_flag_agent",
            "comparison_agent": "comparison_agent"
        }
    )

    # Route agent outputs to LangChain LLM synthesis node
    builder.add_edge("research_agent", "llm_synthesis")
    builder.add_edge("red_flag_agent", "llm_synthesis")
    builder.add_edge("comparison_agent", "llm_synthesis")

    # Synthesis node terminates the graph
    builder.add_edge("llm_synthesis", END)

    return builder.compile()

# Global compiled graph instance
financial_langgraph = build_financial_research_graph()

def run_langgraph_research(session_id: str, query: str, document_id: Optional[str] = None) -> Dict[str, Any]:
    """Executes the compiled LangGraph workflow for financial research."""
    initial_state: FinancialAgentState = {
        "session_id": session_id,
        "query": query,
        "document_id": document_id,
        "intent": "research",
        "sub_topics": [],
        "retrieved_chunks": [],
        "verified_metrics": [],
        "findings": [],
        "sources": [],
        "final_answer": "",
        "agent_used": "",
        "suggested_queries": None
    }

    result = financial_langgraph.invoke(initial_state)

    # Record in research_queries table for conversation history
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT INTO research_queries (id, session_id, query_text, answer_text, agent_used, sources, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            session_id,
            query,
            result.get("final_answer", ""),
            result.get("agent_used", "LangGraph Agent"),
            json.dumps(result.get("sources", [])),
            now
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"[LangGraph] Failed to persist chat query: {e}")

    return {
        "message": query,
        "intent": result.get("intent", "research"),
        "answer": result.get("final_answer", ""),
        "sources": result.get("sources", []),
        "agent_used": result.get("agent_used", "LangGraph Multi-Agent System"),
        "suggested_queries": result.get("suggested_queries")
    }
