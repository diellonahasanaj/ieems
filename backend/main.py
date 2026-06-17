import os
from fastapi import FastAPI, UploadFile, File
from orchestrator.pipeline import run_pipeline

app = FastAPI()

os.makedirs("run_storage", exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "IEEMS Platform Active"}

@app.post("/upload")
async def upload_file(run_id: str, file: UploadFile = File(...)):
    base_path = f"run_storage/{run_id}/artifacts"
    os.makedirs(base_path, exist_ok=True)
    
    file_path = os.path.join(base_path, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    return {"status": "success", "run_id": run_id, "file": file.filename}

@app.post("/run")
async def run_process(run_id: str, employee_id: str, cost_center: str):
    data = {
        "run_id": run_id,
        "employee_id": employee_id,
        "cost_center": cost_center
    }
    result = await run_pipeline(data)
    return result