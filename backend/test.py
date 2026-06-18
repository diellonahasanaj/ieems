import asyncio
from orchestrator.pipeline import run_pipeline

data = {
    "run_id": "run_001",
    "employee_id": "EMP001",
    "cost_center": "SALES"
}

result = asyncio.run(
    run_pipeline(data)
)

print(result)