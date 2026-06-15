import json
import os

def run_pipeline(data):
    run_id = data.get("run_id", "run_001")

    path = f"run_storage/{run_id}/metadata"

    context = {
        "employee_id": "EMP001",
        "cost_center": "IT",
        "status": "processing"
    }

    os.makedirs(path, exist_ok=True)

    with open(f"{path}/context.json", "w") as f:
        json.dump(context, f, indent=4)

    return {
        "status": "completed",
        "step": "context_created"
    }