import requests
import os

BASE_URL = "http://127.0.0.1:8000"

def test_pipeline_flow():
    print("--- 1. Testing Home Endpoint ---")
    home_res = requests.get(f"{BASE_URL}/")
    print("Home Response:", home_res.json())
    
    print("\n--- 2. Testing File Ingestion (/upload) ---")
    dummy_filename = "dummy_receipt.pdf"
    with open(dummy_filename, "wb") as f:
        f.write(b"%PDF-1.4 mock pdf data for testing")
        
    with open(dummy_filename, "rb") as f:
        files = {"file": (dummy_filename, f, "application/pdf")}
        upload_res = requests.post(f"{BASE_URL}/upload", files=files)
        
    upload_data = upload_res.json()
    print("Upload Response:", upload_data)
    
    if os.path.exists(dummy_filename):
        os.remove(dummy_filename)
        
    run_id = upload_data.get("run_id")
    print(f"\nGenerated Run ID from Ingestion: {run_id}")

    print("\n--- 3. Testing Core Agent Pipeline (/run) ---")
    run_res = requests.post(f"{BASE_URL}/run")
    print("Pipeline Execution Response:", run_res.json())

if __name__ == "__main__":
    test_pipeline_flow()