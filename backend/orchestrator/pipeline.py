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
    duplicate_check: Dict[str, Any]
    decision: str

def save_json(path, filename, data):
    os.makedirs(path, exist_ok=True)
    with open(f"{path}/{filename}", "w") as f:
        json.dump(data, f, indent=4)

def agent_a_context(state: PipelineState):
    context = {
        "employee_id": "EMP001",
        "cost_center": "IT",
        "policy_profile": "STANDARD",
        "status": "processing"
    }
    save_json(state["base_path"], "context.json", context)
    return {"context": context}

def agent_b_extract(state: PipelineState):
    extracted = {
        "vendor": "Restaurant ABC",
        "amount": 25,
        "currency": "EUR",
        "date": "2026-06-16"
    }
    save_json(state["base_path"], "extracted_expenses.json", extracted)
    return {"extracted": extracted}

def agent_c_compliance(state: PipelineState):
    compliance = {
        "status": "OK",
        "violations": []
    }
    save_json(state["base_path"], "policy_results.json", compliance)
    return {"compliance": compliance}

def agent_d_normalize(state: PipelineState):
    extracted = state["extracted"]
    normalized = {
        "original_amount": extracted.get("amount"),
        "currency": extracted.get("currency"),
        "amount_usd": 27  
    }
    save_json(state["base_path"], "normalized_expenses.json", normalized)
    return {"normalized": normalized}

def agent_e_duplicate(state: PipelineState):
    duplicate_check = {
        "is_duplicate": False,
        "similarity_score": 0.0,
        "matched_run_id": None
    }
    save_json(state["base_path"], "duplicate_results.json", duplicate_check)
    return {"duplicate_check": duplicate_check}

def generate_audit_log(base_path, run_id, context, extracted, compliance, normalized, duplicate_check, decision):
    markdown_content = f"""# IEEMS SYSTEM AUDIT LOG
=========================================
RUN ID: {run_id}
FINAL DECISION: {decision}
=========================================

## 1. INTAKE CONTEXT (Agent A)
* Employee ID: {context['employee_id']}
* Cost Center: {context['cost_center']}
* Policy Profile: {context['policy_profile']}

## 2. EXTRACTION TELEMETRY (Agent B)
* Vendor: {extracted['vendor']}
* Raw Amount: {extracted['amount']} {extracted['currency']}
* Expense Date: {extracted['date']}

## 3. COMPLIANCE VERIFICATION (Agent C)
* Status: {compliance['status']}
* Total Violations Detected: {len(compliance['violations'])}

## 4. NORMALIZATION METRICS (Agent D)
* Converted Amount (USD): ${normalized['amount_usd']}

## 5. DUPLICATE DETECTION (Agent E)
* Is Duplicate: {duplicate_check['is_duplicate']}
* Similarity Score: {duplicate_check['similarity_score']}

=========================================
END OF AUDIT TRAIL
"""
    with open(f"{base_path}/audit_log.md", "w") as f:
        f.write(markdown_content)

def generate_erp_payload(base_path, run_id, extracted, normalized, decision):
    if decision == "APPROVE":
        erp_data = {
            "transaction_id": run_id,
            "gl_account": "520100",
            "amount": normalized["amount_usd"],
            "currency": "USD",
            "vendor_clean": extracted["vendor"].upper(),
            "status": "READY_FOR_POSTING"
        }
    else:
        erp_data = {
            "transaction_id": run_id,
            "status": "HOLD",
            "reason": f"Pipeline finalized with status: {decision}"
        }
    with open(f"{base_path}/posting_payload.json", "w") as f:
        json.dump(erp_data, f, indent=4)

def agent_h_decision(state: PipelineState):
    compliance = state["compliance"]
    normalized = state["normalized"]
    duplicate_check = state["duplicate_check"]
    
    decision = "APPROVE"
    if compliance.get("violations") or duplicate_check.get("is_duplicate"):
        decision = "REJECT"
    elif normalized.get("amount_usd", 0) > 100:
        decision = "MANUAL_REVIEW"

    final_output = {
        "run_id": state["run_id"],
        "context": state["context"],
        "extracted": state["extracted"],
        "compliance": compliance,
        "normalized": normalized,
        "duplicate_check": duplicate_check,
        "decision": decision
    }
    save_json(state["base_path"], "approval_packet.json", final_output)
    
    generate_audit_log(
        state["base_path"], 
        state["run_id"], 
        state["context"], 
        state["extracted"], 
        compliance, 
        normalized, 
        duplicate_check, 
        decision
    )
    generate_erp_payload(
        state["base_path"], 
        state["run_id"], 
        state["extracted"], 
        normalized, 
        decision
    )
    
    return {"decision": decision}

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
        "duplicate_check": {},
        "decision": ""
    }
    final_state = app_graph.invoke(initial_state)
    return {
        "status": "completed",
        "run_id": final_state["run_id"],
        "decision": final_state["decision"]
    }