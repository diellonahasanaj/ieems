import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - exercised only when RapidFuzz is absent
    fuzz = None


DUPLICATE_THRESHOLD = 85.0
MANUAL_REVIEW_THRESHOLD = 70.0
AMOUNT_TOLERANCE = 1.0
DATE_TOLERANCE_DAYS = 1


def agent_e_duplicate(state: dict):
    """
    AGENT E: Duplicate Detection Agent.
    Compares the current normalized expense against previous run metadata using
    vendor, amount, and date similarity, then writes an auditable duplicates.md.
    """
    base_path = state.get("base_path") or _metadata_path(state)
    run_id = state.get("run_id", "run_001")

    current_expense = _current_expense(state, base_path)
    historical_expenses = _historical_expenses(base_path, run_id)
    matches = [_score_match(current_expense, previous) for previous in historical_expenses]
    matches = [match for match in matches if match["similarity_score"] >= MANUAL_REVIEW_THRESHOLD]
    matches.sort(key=lambda item: item["similarity_score"], reverse=True)

    best_match = matches[0] if matches else None
    is_duplicate = bool(
        best_match
        and best_match["similarity_score"] >= DUPLICATE_THRESHOLD
        and best_match["amount_difference"] <= AMOUNT_TOLERANCE
        and best_match["date_difference_days"] is not None
        and best_match["date_difference_days"] <= DATE_TOLERANCE_DAYS
    )

    result = {
        "agent": "Agent E - Duplicate Detection Agent",
        "status": "DUPLICATE_FOUND" if is_duplicate else "CLEAR",
        "is_duplicate": is_duplicate,
        "similarity_score": best_match["similarity_score"] if best_match else 0.0,
        "matched_run_id": best_match["run_id"] if best_match else None,
        "matched_expense": best_match["expense"] if best_match else None,
        "current_expense": current_expense,
        "thresholds": {
            "duplicate_score": DUPLICATE_THRESHOLD,
            "manual_review_score": MANUAL_REVIEW_THRESHOLD,
            "amount_tolerance": AMOUNT_TOLERANCE,
            "date_tolerance_days": DATE_TOLERANCE_DAYS,
        },
        "matches_reviewed": matches[:10],
        "historical_records_checked": len(historical_expenses),
        "heuristics": _fraud_heuristics(best_match, is_duplicate),
    }

    os.makedirs(base_path, exist_ok=True)
    with open(os.path.join(base_path, "duplicate_results.json"), "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4)
    with open(os.path.join(base_path, "duplicates.md"), "w", encoding="utf-8") as file:
        file.write(_markdown_report(run_id, result))

    return {"duplicate_check": result}


def _metadata_path(state: dict) -> str:
    run_id = state.get("run_id", "run_001")
    return os.path.join("run_storage", run_id, "metadata")


def _current_expense(state: Dict[str, Any], base_path: str) -> Dict[str, Any]:
    normalized = _load_json(os.path.join(base_path, "normalized_expenses.json"))
    extracted = _load_json(os.path.join(base_path, "extracted_expenses.json"))

    if isinstance(state.get("normalized"), dict) and state["normalized"]:
        normalized = state["normalized"]
    if isinstance(state.get("extracted"), dict) and state["extracted"]:
        extracted = state["extracted"]

    expense = _expense_from_packets(normalized, extracted)
    expense["source"] = "current_run"
    return expense


def _expense_from_packets(normalized: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
    raw_extracted = extracted.get("raw_extracted", {}) if isinstance(extracted, dict) else {}
    extracted_record = _first_expense(extracted)

    vendor = (
        normalized.get("vendor")
        or extracted_record.get("vendor")
        or raw_extracted.get("vendor")
        or "UNKNOWN"
    )
    amount = (
        normalized.get("amount")
        or normalized.get("original_amount")
        or extracted_record.get("amount")
        or raw_extracted.get("amount")
        or 0
    )
    date = (
        normalized.get("standard_date")
        or normalized.get("date")
        or extracted_record.get("date")
        or raw_extracted.get("date")
        or "UNKNOWN"
    )
    currency = (
        normalized.get("standard_currency")
        or normalized.get("currency")
        or normalized.get("original_currency")
        or extracted_record.get("currency")
        or raw_extracted.get("currency")
        or "EUR"
    )

    return {
        "vendor": str(vendor).strip(),
        "amount": _parse_amount(amount),
        "currency": str(currency).strip().upper(),
        "date": _normalize_date(date),
    }


def _first_expense(packet: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(packet, dict):
        return {}
    for key in ("expenses", "items"):
        if isinstance(packet.get(key), list) and packet[key]:
            first = packet[key][0]
            return first if isinstance(first, dict) else {}
    if any(key in packet for key in ("vendor", "amount", "date", "currency")):
        return packet
    return {}


def _historical_expenses(base_path: str, current_run_id: str) -> List[Dict[str, Any]]:
    run_storage = _run_storage_dir(base_path)
    if not os.path.isdir(run_storage):
        return []

    records: List[Dict[str, Any]] = []
    for run_id in sorted(os.listdir(run_storage)):
        if run_id == current_run_id:
            continue
        metadata_dir = os.path.join(run_storage, run_id, "metadata")
        if not os.path.isdir(metadata_dir):
            continue

        normalized = _load_json(os.path.join(metadata_dir, "normalized_expenses.json"))
        extracted = _load_json(os.path.join(metadata_dir, "extracted_expenses.json"))
        approval = _load_json(os.path.join(metadata_dir, "approval_packet.json"))

        if not normalized and isinstance(approval.get("normalized"), dict):
            normalized = approval["normalized"]
        if not extracted and isinstance(approval.get("extracted"), dict):
            extracted = approval["extracted"]

        expense = _expense_from_packets(normalized, extracted)
        if expense["vendor"] == "UNKNOWN" and expense["amount"] == 0.0 and expense["date"] == "UNKNOWN":
            continue
        expense["run_id"] = run_id
        expense["source"] = metadata_dir
        records.append(expense)

    return records


def _run_storage_dir(base_path: str) -> str:
    metadata_dir = os.path.abspath(base_path)
    run_dir = os.path.dirname(metadata_dir)
    return os.path.dirname(run_dir)


def _score_match(current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
    vendor_score = _vendor_similarity(current["vendor"], previous["vendor"])
    amount_difference = abs(current["amount"] - previous["amount"])
    amount_score = _amount_similarity(current["amount"], previous["amount"])
    date_difference = _date_difference_days(current["date"], previous["date"])
    date_score = _date_similarity(date_difference)

    similarity_score = round((vendor_score * 0.5) + (amount_score * 0.3) + (date_score * 0.2), 2)

    return {
        "run_id": previous.get("run_id"),
        "similarity_score": similarity_score,
        "vendor_score": round(vendor_score, 2),
        "amount_score": round(amount_score, 2),
        "date_score": round(date_score, 2),
        "amount_difference": round(amount_difference, 2),
        "date_difference_days": date_difference,
        "expense": {
            "vendor": previous["vendor"],
            "amount": previous["amount"],
            "currency": previous["currency"],
            "date": previous["date"],
        },
    }


def _vendor_similarity(left: str, right: str) -> float:
    left_normalized = _normalize_vendor(left)
    right_normalized = _normalize_vendor(right)
    if not left_normalized or not right_normalized:
        return 0.0
    if fuzz:
        return float(fuzz.token_set_ratio(left_normalized, right_normalized))
    return SequenceMatcher(None, left_normalized, right_normalized).ratio() * 100


def _amount_similarity(left: float, right: float) -> float:
    if left == right:
        return 100.0
    largest = max(abs(left), abs(right), 1.0)
    difference_ratio = min(abs(left - right) / largest, 1.0)
    return max(0.0, 100.0 - (difference_ratio * 100.0))


def _date_similarity(date_difference: Optional[int]) -> float:
    if date_difference is None:
        return 50.0
    if date_difference == 0:
        return 100.0
    if date_difference <= 1:
        return 85.0
    if date_difference <= 3:
        return 70.0
    if date_difference <= 7:
        return 40.0
    return 0.0


def _fraud_heuristics(best_match: Optional[Dict[str, Any]], is_duplicate: bool) -> List[str]:
    if not best_match:
        return ["No historical expense exceeded the manual review similarity threshold."]

    heuristics = []
    if is_duplicate:
        heuristics.append("Vendor, amount, and date strongly match a previous report.")
    if best_match["vendor_score"] >= 90:
        heuristics.append("Vendor name is highly similar after normalization.")
    if best_match["amount_difference"] <= AMOUNT_TOLERANCE:
        heuristics.append("Amount is within duplicate tolerance.")
    if best_match["date_difference_days"] is not None and best_match["date_difference_days"] <= DATE_TOLERANCE_DAYS:
        heuristics.append("Expense date is exact or near-exact.")
    return heuristics


def _markdown_report(run_id: str, result: Dict[str, Any]) -> str:
    lines = [
        "# Duplicate Detection Report",
        "",
        f"Run ID: {run_id}",
        f"Status: {result['status']}",
        f"Is Duplicate: {result['is_duplicate']}",
        f"Similarity Score: {result['similarity_score']}",
        f"Matched Run ID: {result['matched_run_id'] or 'None'}",
        f"Historical Records Checked: {result['historical_records_checked']}",
        "",
        "## Current Expense",
        f"- Vendor: {result['current_expense']['vendor']}",
        f"- Amount: {result['current_expense']['amount']} {result['current_expense']['currency']}",
        f"- Date: {result['current_expense']['date']}",
        "",
        "## Fraud Prevention Heuristics",
    ]
    lines.extend(f"- {heuristic}" for heuristic in result["heuristics"])

    if result["matches_reviewed"]:
        lines.extend(["", "## Similar Historical Matches"])
        for match in result["matches_reviewed"]:
            lines.extend(
                [
                    f"- Run: {match['run_id']}",
                    f"  Score: {match['similarity_score']}",
                    f"  Vendor Score: {match['vendor_score']}",
                    f"  Amount Difference: {match['amount_difference']}",
                    f"  Date Difference Days: {match['date_difference_days']}",
                ]
            )

    lines.append("")
    return "\n".join(lines)


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _parse_amount(value: Any) -> float:
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    cleaned = re.sub(r"[^\d,.\-]", "", str(value or "0")).strip()
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return 0.0


def _normalize_date(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw or raw.upper() == "UNKNOWN":
        return "UNKNOWN"

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _date_difference_days(left: str, right: str) -> Optional[int]:
    try:
        left_date = datetime.strptime(left, "%Y-%m-%d").date()
        right_date = datetime.strptime(right, "%Y-%m-%d").date()
    except ValueError:
        return None
    return abs((left_date - right_date).days)


def _normalize_vendor(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9 ]", " ", str(value or "").lower())
    normalized = re.sub(r"\b(ltd|llc|inc|shpk|gmbh|sarl|the)\b", " ", normalized)
    return " ".join(normalized.split())
