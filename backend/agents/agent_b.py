import os
import re
import json
from typing import Dict, Any

from agents.utils_ocr import extract_text_and_boxes


def parse_extracted_text(text: str):

    parsed = {
        "vendor": "UNKNOWN",
        "amount": "0.00",
        "date": "UNKNOWN",
        "currency": "EUR"
    }

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    if lines:
        parsed["vendor"] = lines[0]

    amount_patterns = [
        r"(?:total|grand total|amount|due|balance)\s*[:\s]*[€$]?\s*(\d+[.,]\d{2})",
        r"(\d+[.,]\d{2})\s*(?:EUR|USD|ALL|€|\$)"
    ]

    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            parsed["amount"] = match.group(1)
            break

    date_patterns = [
        r"\d{2}/\d{2}/\d{4}",
        r"\d{4}-\d{2}-\d{2}",
        r"\d{2}\.\d{2}\.\d{4}"
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text)

        if match:
            parsed["date"] = match.group()
            break

    upper_text = text.upper()

    if "USD" in upper_text or "$" in text:
        parsed["currency"] = "USD"

    elif "ALL" in upper_text or "LEK" in upper_text:
        parsed["currency"] = "ALL"

    else:
        parsed["currency"] = "EUR"

    return parsed


def agent_b_extract(state: Dict[str, Any]) -> Dict[str, Any]:

    print("[Agent B] OCR & Extraction")

    context = state.get("context", {})

    doc_info = context.get(
        "document_classification",
        {}
    )

    image_path = doc_info.get(
        "absolute_file_path"
    )

    base_path = state.get("base_path")

    if not image_path:
        raise ValueError(
            "No file path received from Agent A"
        )

    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)

    full_text, boxes, confidence = (
        extract_text_and_boxes(image_path)
    )

    extracted_data = parse_extracted_text(
        full_text
    )

    extracted_output = {
        "raw_text": full_text,
        "raw_extracted": extracted_data,
        "confidence_score": confidence,
        "traceability_boxes": boxes
    }

    os.makedirs(base_path, exist_ok=True)

    with open(
        os.path.join(
            base_path,
            "extracted_expenses.json"
        ),
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            extracted_output,
            f,
            indent=4,
            ensure_ascii=False
        )

    return {
        "extracted": extracted_output
    }