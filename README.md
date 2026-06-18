# Intelligent Employee Expense Management System (IEEMS)
IEEMS is an automated platform for processing, verifying, and approving employee expense receipts. Built using **FastAPI** and **LangGraph**, it leverages an asynchronous **Multi-Agent Architecture** for end-to-end corporate expense governance.


## 🏗️ Multi-Agent Pipeline
The system securely orchestrates data through a state-driven graph using 6 specialized agents:
* **Agent A (Intake):** Validates file formats and applies routing policies based on the employee's department.
* **Agent B (OCR):** Extracts raw text, amounts, dates, and currencies using EasyOCR and OpenCV.
* **Agent C (Compliance):** Cross-checks extracted data against internal company spending limits.
* **Agent D (Normalization):** Standardizes formats, cleans strings, and converts currencies to EUR.
* **Agent E (Duplicate Check):** Scans past transaction history to flag potential duplicate submissions.
* **Agent H (Final Decision):** Issues the final status (`APPROVED`, `REJECTED`, `MANUAL_REVIEW`) and saves JSON logs for auditing.


## 🛠️ Tech Stack
* **Frameworks:** FastAPI, LangGraph, Uvicorn, Pydantic
* **Data & ML:** EasyOCR, OpenCV, Pandas, Pillow

## 🚀 How to Run

### 1. Install Dependencies
pip install fastapi uvicorn langgraph opencv-python easyocr pandas pillow rapidfuzz requests
2. Start the Server
uvicorn main:app --reload
3. Test via Swagger UI
Open your browser and go to: http://127.0.0.1:8000/docs

Use /upload to send the receipt image or PDF.

Use /run to execute the full agent workflow.
