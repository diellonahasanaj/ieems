import requests
import os

BASE_URL = "http://127.0.0.1:8000"

def test_pipeline_flow():
    print("==================================================")
    print("    IEEMS INTEGRATION PIPELINE TEST SUITE        ")
    print("==================================================")
    
    print("\n--- [STEP 1] Testing Home Endpoint ---")
    try:
        home_res = requests.get(f"{BASE_URL}/")
        print("Status Code:", home_res.status_code)
        print("Home Response:", home_res.json())
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR]: Could not connect to the server at {BASE_URL}.")
        print("👉 Make sure your Uvicorn server is running in your other terminal pane!")
        return
    
    print("\n--- [STEP 2] Testing File Ingestion (/upload) ---")
    dummy_filename = "dummy_receipt.pdf"
    
    with open(dummy_filename, "wb") as f:
        f.write(b"%PDF-1.4\n%mock pdf payload")
        
    try:
        with open(dummy_filename, "rb") as f:
            files = {"file": (dummy_filename, f, "application/pdf")}
            upload_res = requests.post(f"{BASE_URL}/upload", files=files)
            
        upload_data = upload_res.json()
        print("Status Code:", upload_res.status_code)
        print("Upload Response:", upload_data)
        
        run_id = upload_data.get("run_id")
        if not run_id:
            print("\n[ERROR]: Server failed to return a valid 'run_id'. Execution aborted.")
            return
            
        print(f"🎯 Successfully tracked Run ID: {run_id}")

        print("\n--- [STEP 3] Testing Core Agent Pipeline (/run) ---")
        print(f"Sending processing request for targeting space: {run_id}...")
        
        run_res = requests.post(f"{BASE_URL}/run?run_id={run_id}")
        
        print("Status Code:", run_res.status_code)
        print("Pipeline Execution Response:", run_res.json())
        print("\n==================================================")
        print("         TEST FLOW EXECUTION COMPLETED            ")
        print("==================================================")
        
    except Exception as e:
        print(f"\n[ERROR]: An error occurred during endpoint testing: {str(e)}")
        
    finally:
        if os.path.exists(dummy_filename):
            os.remove(dummy_filename)
            print(f"\n[INFO]: Temporary environment file '{dummy_filename}' scrubbed clean.")

if __name__ == "__main__":
    test_pipeline_flow()
