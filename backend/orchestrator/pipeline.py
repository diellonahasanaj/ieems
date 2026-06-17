import json
import os
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END

class PipelineState(TypedDict):
    run_id: str
    base_path: str
    context: Dict[str, Any]
    extracted: Dict[str, Any]
    compliance: Dict[str, Any]
    normalized: Dict[str, Any]
    decision: str

def save_json(path, filename, data):
    os.makedirs(path, exist_ok=True)
    with open(f"{path}/{filename}", "w") as f:
        json.dump(data, f, indent=4)

def agent_a_node(state: PipelineState):
    context = {
        "employee_id": "EMP001",
        "cost_center": "IT",
        "policy_profile": "STANDARD",
        "status": "processing"
    }
    save_json(state["base_path"], "context.json", context)
    return {"context": context}

def agent_b_node(state: PipelineState):
    extracted = {
        "vendor": "Restaurant ABC",
        "amount": 25,
        "currency": "EUR",
        "date": "2026-06-16"
    }
    save_json(state["base_path"], "extracted_expenses.json", extracted)
    return {"extracted": extracted}

def agent_c_node(state: PipelineState):
    compliance = {
        "status": "OK",
        "violations": []
    }
    save_json(state["base_path"], "policy_results.json", compliance)
    return {"compliance": compliance}

def agent_d_node(state: PipelineState):
    extracted = state["extracted"]
    normalized = {
        "original_amount": extracted.get("amount"),
        "currency": extracted.get("currency"),
        "amount_usd": 27  
    }
    save_json(state["base_path"], "normalized_expenses.json", normalized)
    return {"normalized": normalized}

def agent_h_node(state: PipelineState):
    compliance = state["compliance"]
    normalized = state["normalized"]
    
    decision = "APPROVE"
    if compliance.get("violations"):
        decision = "REJECT"
    elif normalized.get("amount_usd", 0) > 100:
        decision = "MANUAL_REVIEW"

    final_output = {
        "run_id": state["run_id"],
        "context": state["context"],
        "extracted": state["extracted"],
        "compliance": compliance,
        "normalized": normalized,
        "decision": decision
    }
    save_json(state["base_path"], "approval_packet.json", final_output)
    
    return {"decision": decision}

workflow = StateGraph(PipelineState)

# Add all nodes
workflow.add_node("agent_a", agent_a_node)
workflow.add_node("agent_b", agent_b_node)
workflow.add_node("agent_c", agent_c_node)
workflow.add_node("agent_d", agent_d_node)
workflow.add_node("agent_h", agent_h_node)

workflow.set_entry_point("agent_a")
workflow.add_edge("agent_a", "agent_b")
workflow.add_edge("agent_b", "agent_c")
workflow.add_edge("agent_c", "agent_d")
workflow.add_edge("agent_d", "agent_h")
workflow.add_edge("agent_h", END)

app_graph = workflow.compile()

def run_pipeline(data):
    run_id = data.get("run_id", "run_001")
    base_path = f"run_storage/{run_id}/metadata"
    
    initial_state = {
        "run_id": run_id,
        "base_path": base_path,
        "context": {},
        "extracted": {},
        "compliance": {},
        "normalized": {},
        "decision": ""
    }
    
    final_state = app_graph.invoke(initial_state)
    
    return {
        "status": "completed",
        "run_id": final_state["run_id"],
        "decision": final_state["decision"]
    }