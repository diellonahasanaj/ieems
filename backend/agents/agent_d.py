import os
import re
import json
import pandas as pd
from typing import Dict, Any


def normalize_amount(amount_value: Any) -> float:
    """
    Pastron shumën dhe e kthen në float.
    """
    if isinstance(amount_value, (int, float)):
        return float(amount_value)

    try:
        cleaned = re.sub(r"[^\d,\.]", "", str(amount_value))

        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")

        return float(cleaned)

    except Exception:
        return 0.0


def normalize_date(date_str: str) -> str:
    """
    Standardizon datën në YYYY-MM-DD.
    """

    if not date_str or date_str == "UNKNOWN":
        return "1970-01-01"

    try:
        parsed = pd.to_datetime(
            date_str,
            errors="coerce",
            dayfirst=True
        )

        if pd.isna(parsed):
            return "1970-01-01"

        return parsed.strftime("%Y-%m-%d")

    except Exception:
        return "1970-01-01"


def convert_to_eur(amount: float, currency: str) -> float:
    """
    Currency conversion MVP.
    """

    rates = {
        "EUR": 1.0,
        "USD": 0.92,
        "ALL": 0.01
    }

    rate = rates.get(currency.upper(), 1.0)

    return round(amount * rate, 2)


def perform_reconciliation(amount: float) -> Dict[str, Any]:
    """
    Basic reconciliation logic.
    """

    if amount < 0:
        return {
            "status": "FAILED",
            "reason": "Negative amount"
        }

    return {
        "status": "SUCCESS",
        "reason": "Validation passed"
    }


def agent_d_normalize(state: Dict[str, Any]) -> Dict[str, Any]:

    print("[Agent D] Normalization & Reconciliation")

    extracted_node = state.get("extracted", {})

    raw_extracted = extracted_node.get(
        "raw_extracted",
        {}
    )

    base_path = state.get("base_path")

    vendor = raw_extracted.get(
        "vendor",
        "UNKNOWN"
    )

    amount_raw = raw_extracted.get(
        "amount",
        "0.00"
    )

    date_raw = raw_extracted.get(
        "date",
        "UNKNOWN"
    )

    currency = raw_extracted.get(
        "currency",
        "EUR"
    ).upper()

    cleaned_amount = normalize_amount(
        amount_raw
    )

    standardized_date = normalize_date(
        date_raw
    )

    eur_amount = convert_to_eur(
        cleaned_amount,
        currency
    )

    reconciliation = perform_reconciliation(
        eur_amount
    )

    normalized_output = {
        "vendor": vendor.upper(),
        "original_amount": cleaned_amount,
        "original_currency": currency,
        "amount": eur_amount,
        "standard_currency": "EUR",
        "standard_date": standardized_date,
        "reconciliation": reconciliation
    }

    os.makedirs(base_path, exist_ok=True)

    output_file = os.path.join(
        base_path,
        "normalized_expenses.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            normalized_output,
            f,
            indent=4,
            ensure_ascii=False
        )

    updated_extracted = extracted_node.copy()
    updated_extracted["amount"] = eur_amount

    return {
        "normalized": normalized_output,
        "extracted": updated_extracted
    }