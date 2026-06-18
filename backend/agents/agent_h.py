import os
import json
from typing import Dict, Any

def agent_h_decision(state: Dict[str, Any]) -> Dict[str, Any]:
    print("[Agent H] Running final decision logic...")

    extracted_data = state.get("extracted", {})
    compliance_data = state.get("compliance", {})
    duplicate_data = state.get("duplicate_check", {})
    
    total_amount = extracted_data.get("amount", 0.0)
    
    if duplicate_data.get("is_duplicate") is True:
        final_decision = "REJECTED"
        reason = "Fraud Alert: This invoice has already been processed in a previous run."
        
    elif compliance_data.get("status") == "FAILED":
        final_decision = "REJECTED"
        reason = f"Policy Violation: {compliance_data.get('reason', 'Failed compliance check.')}"
        
    elif total_amount > 5000.0:
        final_decision = "MANUAL_REVIEW"
        reason = f"Amount {total_amount} exceeds automatic approval threshold (€5000)."
        
    else:
        final_decision = "APPROVED"
        reason = "All automated agent checks passed successfully."

    print(f"[Agent H] Decision: {final_decision} | Reason: {reason}")

    base_path = state.get("base_path")
    if base_path:
        os.makedirs(base_path, exist_ok=True)
        approval_packet = {
            "run_id": state.get("run_id"),
            "employee_id": state.get("employee_id"),
            "final_decision": final_decision,
            "reason": reason,
            "metrics": {
                "total_amount": total_amount,
                "currency": state.get("normalized", {}).get("standard_currency", "EUR")
            }
        }
        with open(os.path.join(base_path, "approval_packet.json"), "w") as f:
            json.dump(approval_packet, f, indent=4)

    return {"decision": final_decision}