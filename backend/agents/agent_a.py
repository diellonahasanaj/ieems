import os
import json
from typing import Dict, Any

def agent_a_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    AGENT A: Intake & Context Agent
    Validates uploaded file artifacts, Classifies format, and applies routing policy profiles.
    """
    runtime_inputs = state.get("inputs", {})
    run_id = state.get("run_id")
    base_path = state.get("base_path")
    
    artifact_dir = f"run_storage/{run_id}/artifacts"
    
    # Safety Check: Guard against missing directories or empty uploads
    if not os.path.exists(artifact_dir):
        return {"context": {"system_status": "FAILED_NO_ARTIFACTS", "error": "Artifact directory missing"}}
        
    detected_files = os.listdir(artifact_dir)
    valid_extensions = [".pdf", ".png", ".jpg", ".jpeg", ".xml", ".csv"]
    
    file_name = next((f for f in detected_files if any(f.lower().endswith(ext) for ext in valid_extensions)), None)
    
    if not file_name:
        return {"context": {"system_status": "FAILED_UNSUPPORTED_FORMAT", "error": "No valid file type found"}}

    ext = file_name.split(".")[-1].lower()
    if ext in ["pdf"]:
        file_type = "DIGITAL_PDF"
    elif ext in ["png", "jpg", "jpeg"]:
        file_type = "RECEIPT_IMAGE"
    elif ext in ["xml", "csv"]:
        file_type = "STRUCTURED_DATA"
    else:
        file_type = "UNKNOWN"

    cost_center = runtime_inputs.get("cost_center", "UNASSIGNED").upper()
    
    if cost_center in ["RND", "RESEARCH", "ENG"]:
        policy_profile = "TECHNICAL_RESEARCH_HIGH_LIMIT"
    elif cost_center in ["SALES", "MARKETING"]:
        policy_profile = "TRAVEL_ENTERTAINMENT_FLEX"
    elif cost_center in ["EXEC", "BOARD"]:
        policy_profile = "EXECUTIVE_UNRESTRICTED"
    else:
        policy_profile = "STANDARD_CORPORATE"

    context = {
        "employee_id": runtime_inputs.get("employee_id", "UNKNOWN"),
        "cost_center": cost_center,
        "policy_profile": policy_profile,
        "document_classification": {
            "file_name": file_name,
            "absolute_file_path": os.path.abspath(os.path.join(artifact_dir, file_name)),
            "detected_format": file_type,
            "is_supported": file_type != "UNKNOWN"
        },
        "system_status": "INTAKE_COMPLETE"
    }
    
    os.makedirs(base_path, exist_ok=True)
    with open(f"{base_path}/context_packet.json", "w") as f:
        json.dump(context, f, indent=4)
        
    return {"context": context}