from fastapi import FastAPI, UploadFile
from orchestrator.pipeline import run_pipeline

app = FastAPI()

@app.get("/")
def home():
    return {"message": "IEEMS backend running"}

@app.post("/upload")
def upload(file: UploadFile):
    return {
        "filename": file.filename,
        "status": "uploaded"
    }

@app.post("/run")
def run():
    result = run_pipeline({"dummy": True})
    return result