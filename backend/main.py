import os
import uuid
from fastapi import FastAPI, UploadFile, File
from orchestrator.pipeline import run_pipeline

app = FastAPI()

# --- NEW: Define the missing function ---
def get_next_run_id():
    # Generates a short, unique ID like 'run_a1b2c3'
    unique_suffix = uuid.uuid4().hex[:6]
    return f"run_{unique_suffix}"

@app.get("/")
def home():
    return {"message": "IEEMS backend running"}

@app.post("/upload")
def upload(file: UploadFile):
    run_id = get_next_run_id()

    path = f"run_storage/{run_id}/artifacts"
    os.makedirs(path, exist_ok=True)

    file_path = f"{path}/{file.filename}"

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    return {
        "run_id": run_id,
        "filename": file.filename,
        "status": "saved"
    }

@app.post("/run")
def run(run_id: str):
    result = run_pipeline({"run_id": run_id})
    return result