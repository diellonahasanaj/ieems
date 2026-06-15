from fastapi import FastAPI, UploadFile
from orchestrator.pipeline import run_pipeline

app = FastAPI()

@app.get("/")
def home():
    return {"message": "IEEMS backend running"}

import os
from fastapi import UploadFile, File

@app.post("/upload")
def upload(file: UploadFile = File(...)):
    try:
        path = "run_storage/run_001/artifacts"
        os.makedirs(path, exist_ok=True)

        file_location = os.path.join(path, file.filename)

        with open(file_location, "wb") as f:
            f.write(file.file.read())

        return {
            "filename": file.filename,
            "status": "saved",
            "path": file_location
        }

    except Exception as e:
        return {
            "error": str(e)
        }

@app.post("/run")
def run():
    result = run_pipeline({"dummy": True})
    return result