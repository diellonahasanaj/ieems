import uuid
import os
from fastapi import FastAPI, UploadFile, File
from orchestrator.pipeline import run_pipeline

app = FastAPI()

STORAGE_DIR = "run_storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

@app.get("/")
def home():
    return {"message": "IEEMS backend running"}

@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    run_id = f"run_{uuid.uuid4().hex[:6]}"
    run_dir = os.path.join(STORAGE_DIR, run_id, "artifacts")
    os.makedirs(run_dir, exist_ok=True)
    
    file_path = os.path.join(run_dir, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
        
    return {
        "status": "saved",
        "filename": file.filename,
        "run_id": run_id
    }

@app.post("/run")
def run(run_id: str, employee_id: str = "EMP001", cost_center: str = "IT"):
    result = run_pipeline({
        "run_id": run_id,
        "employee_id": employee_id,
        "cost_center": cost_center
    })
    return result