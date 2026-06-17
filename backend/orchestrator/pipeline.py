import json
import os
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END

from agents.agent_a import agent_a_context
from agents.agent_b import agent_b_extract
from agents.agent_c import agent_c_compliance
from agents.agent_d import agent_d_normalize
from agents.agent_e import agent_e_duplicate
from agents.agent_h import agent_h_decision

class PipelineState(TypedDict):
    run_id: str
    base_path: str
    inputs: Dict[str, Any]
    context: Dict[str, Any]
    extracted: Dict[str, Any]
    compliance: Dict[str, Any]
    normalized: Dict[str, Any]
    duplicate_check: Dict[str, Any]
    decision: str

workflow = StateGraph(PipelineState)

workflow.add_node("agent_a", agent_a_context)
workflow.add_node("agent_b", agent_b_extract)
workflow.add_node("agent_c", agent_c_compliance)
workflow.add_node("agent_d", agent_d_normalize)
workflow.add_node("agent_e", agent_e_duplicate)
workflow.add_node("agent_h", agent_h_decision)

workflow.set_entry_point("agent_a")
workflow.add_edge("agent_a", "agent_b")
workflow.add_edge("agent_b", "agent_c")  
workflow.add_edge("agent_c", "agent_d")
workflow.add_edge("agent_d", "agent_e")
workflow.add_edge("agent_e", "agent_h")
workflow.add_edge("agent_h", END)

app_graph = workflow.compile()

async def run_pipeline(data: Dict[str, Any]) -> Dict[str, Any]:
    run_id = data.get("run_id", "run_001")
    base_path = f"run_storage/{run_id}/metadata"
    
    initial_state = {
        "run_id": run_id,
        "base_path": base_path,
        "inputs": {
            "employee_id": data.get("employee_id"),
            "cost_center": data.get("cost_center")
        },
        "context": {},
        "extracted": {},
        "compliance": {},
        "normalized": {},
        "duplicate_check": {},
        "decision": ""
    }

    final_state = await app_graph.ainvoke(initial_state)
    
    return {
        "status": "completed",
        "run_id": final_state["run_id"],
        "decision": final_state["decision"]
    }