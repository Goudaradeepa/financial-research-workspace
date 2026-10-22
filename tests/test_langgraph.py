import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from langgraph_orchestrator import (
    build_financial_research_graph,
    run_langgraph_research,
    financial_langgraph,
    FinancialAgentState
)

client = TestClient(app)
SEED_SESSION = "seed-session-flagship-reports"

def test_langgraph_graph_compilation():
    """Verifies LangGraph StateGraph builds and compiles with all required agent nodes."""
    graph = build_financial_research_graph()
    assert graph is not None
    
    # Verify nodes present in the compiled StateGraph
    node_keys = list(graph.nodes.keys())
    assert "supervisor_router" in node_keys
    assert "research_agent" in node_keys
    assert "red_flag_agent" in node_keys
    assert "comparison_agent" in node_keys
    assert "llm_synthesis" in node_keys

def test_langgraph_research_query_execution():
    """Verifies end-to-end execution through the compiled LangGraph workflow."""
    res = run_langgraph_research(
        session_id=SEED_SESSION,
        query="What is Apple's total revenue and operating margin?"
    )
    assert res is not None
    assert res["intent"] == "research"
    assert "Apple" in res["answer"]
    assert "391" in res["answer"]
    assert len(res["sources"]) > 0
    # Every source must have page citation
    for s in res["sources"]:
        assert s["source_page"] is not None

def test_langgraph_comparison_routing():
    """Verifies LangGraph supervisor node routes multi-company queries to the comparison node."""
    res = run_langgraph_research(
        session_id=SEED_SESSION,
        query="Compare Apple vs Microsoft on revenue and profit."
    )
    assert res["intent"] == "comparison"
    assert "Comparison" in res["agent_used"]
    assert "Apple" in res["answer"]
    assert "Microsoft" in res["answer"]

def test_langgraph_red_flags_routing():
    """Verifies LangGraph supervisor node routes risk queries to the red flag node."""
    res = run_langgraph_research(
        session_id=SEED_SESSION,
        query="Are there any major debt risks or auditor qualifications?"
    )
    assert res["intent"] == "red_flags"
    assert "Red Flag" in res["agent_used"]
    assert len(res["answer"]) > 20

def test_langgraph_graph_info_and_health_api():
    """Verifies API exposes LangGraph architecture metadata and health check confirms LangGraph/LangChain."""
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    data = health_res.json()
    assert "LangGraph" in data["orchestration_framework"]
    assert "LangChain" in data["llm_framework"]

    graph_res = client.get(f"/api/sessions/{SEED_SESSION}/graph/info")
    assert graph_res.status_code == 200
    g_data = graph_res.json()
    assert g_data["framework"] == "LangGraph"
    assert g_data["llm_framework"] == "LangChain"
    assert "supervisor_router" in g_data["graph_nodes"]
    assert "llm_synthesis" in g_data["graph_nodes"]
