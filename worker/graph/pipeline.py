"""
graph/pipeline.py

Merangkai seluruh node dan conditional edges menjadi satu LangGraph StateGraph pipeline.
"""

from langgraph.graph import StateGraph, END
from graph.state import AgentState
from graph.supervisor import supervisor_node, route_by_intent

# Import agent nodes
from agents.financial_profile_agent import financial_profile_agent_node
from agents.transaction_agent import transaction_agent_node
from agents.store_transaction_agent import store_transaction_agent_node
from agents.category_budget_agent import category_budget_agent_node
from agents.dashboard_agent import dashboard_agent_node
from agents.analytics_agent import analytics_agent_node
from agents.assets_agent import assets_agent_node
from agents.out_of_context_agent import out_of_context_agent_node

# Import formatter node
from graph.formatter import response_formatter_node

def build_workflow() -> StateGraph:
    """Membangun alur kerja (workflow) LangGraph."""
    workflow = StateGraph(AgentState)
    
    # 1. Tambahkan seluruh Node
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("financial_profile_agent", financial_profile_agent_node)
    workflow.add_node("transaction_agent", transaction_agent_node)
    workflow.add_node("store_transaction_agent", store_transaction_agent_node)
    workflow.add_node("category_budget_agent", category_budget_agent_node)
    workflow.add_node("dashboard_agent", dashboard_agent_node)
    workflow.add_node("analytics_agent", analytics_agent_node)
    workflow.add_node("assets_agent", assets_agent_node)
    workflow.add_node("out_of_context_agent", out_of_context_agent_node)
    workflow.add_node("formatter", response_formatter_node)
    
    # 2. Set Entry Point
    workflow.set_entry_point("supervisor")
    
    # 3. Tambahkan Conditional Edges dari Supervisor ke Sub-Agent
    workflow.add_conditional_edges(
        "supervisor",
        route_by_intent,
        {
            "financial_profile": "financial_profile_agent",
            "transaction_history": "transaction_agent",
            "record_transaction": "store_transaction_agent",
            "category_budget": "category_budget_agent",
            "dashboard_summary": "dashboard_agent",
            "analytics": "analytics_agent",
            "assets": "assets_agent",
            "out_of_context": "out_of_context_agent"
        }
    )
    
    # 4. Tambahkan Edges dari seluruh Sub-Agent menuju Formatter
    workflow.add_edge("financial_profile_agent", "formatter")
    workflow.add_edge("transaction_agent", "formatter")
    workflow.add_edge("store_transaction_agent", "formatter")
    workflow.add_edge("category_budget_agent", "formatter")
    workflow.add_edge("dashboard_agent", "formatter")
    workflow.add_edge("analytics_agent", "formatter")
    workflow.add_edge("assets_agent", "formatter")
    workflow.add_edge("out_of_context_agent", "formatter")
    
    # 5. Edges dari Formatter menuju END
    workflow.add_edge("formatter", END)
    
    return workflow

# Compile graph
workflow = build_workflow()
app_graph = workflow.compile()
