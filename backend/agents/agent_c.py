import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


DEFAULT_POLICIES: Dict[str, Dict[str, Any]] = {
    "STANDARD_CORPORATE": {
        "per_diem_limit": 75.0,
        "category_limits": {
            "meal": 35.0,
            "transport": 150.0,
            "lodging": 250.0,
            "office_supplies": 100.0,
            "misc": 75.0,
        },
        "allow_weekend_expenses": False,
        "receipt_required_over": 25.0,
    },
    "TECHNICAL_RESEARCH_HIGH_LIMIT": {
        "per_diem_limit": 150.0,
        "category_limits": {
            "meal": 50.0,
            "transport": 300.0,
            "lodging": 350.0,
            "office_supplies": 500.0,
            "software": 1000.0,
            "misc": 150.0,
        },
        "allow_weekend_expenses": True,
        "receipt_required_over": 25.0,
    },
    "TRAVEL_ENTERTAINMENT_FLEX": {
        "per_diem_limit": 125.0,
        "category_limits": {
            "meal": 65.0,
            "transport": 250.0,
            "lodging": 325.0,
            "entertainment": 300.0,
            "misc": 125.0,
        },
        "allow_weekend_expenses": True,
        "receipt_required_over": 25.0,
    },
    "EXECUTIVE_UNRESTRICTED": {
        "per_diem_limit": 1000.0,
        "category_limits": {},
        "allow_weekend_expenses": True,
        "receipt_required_over": 250.0,
    },
}


VENDOR_CATEGORY_HINTS = {
    "restaurant": "meal",
    "cafe": "meal",
    "coffee": "meal",
    "hotel": "lodging",
    "inn": "lodging",
    "airline": "transport",
    "taxi": "transport",
    "uber": "transport",
    "office": "office_supplies",
    "software": "software",
    "subscription": "software",
}


def agent_c_compliance(state: dict):
    """
    AGENT C: Policy Validation Agent.
    Validates extracted expenses against the context policy profile and writes
    policy_results.json for downstream agents and auditability.
    """
    base_path = state.get("base_path") or _metadata_path(state)
    context = _load_packet(state.get("context"), base_path, ["context_packet.json", "context.json"])
    extracted = _load_packet(state.get("extracted"), base_path, ["extracted_expenses.json"])

    policy_profile = context.get("policy_profile") or "STANDARD_CORPORATE"
    policy = DEFAULT_POLICIES.get(policy_profile, DEFAULT_POLICIES["STANDARD_CORPORATE"])
    expenses = _coerce_expenses(extracted)
    context_receipt_present = _context_receipt_present(context)

    violations: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    validated_expenses: List[Dict[str, Any]] = []

    if not expenses:
        violations.append(
            _issue(
                "MISSING_EXPENSE_DATA",
                "No extracted expense records were available for policy validation.",
                "REJECT",
            )
        )

    for index, expense in enumerate(expenses, start=1):
        normalized = _normalize_expense(expense, context_receipt_present)
        expense_issues: List[Dict[str, Any]] = []

        amount = normalized.get("amount")
        if amount is None:
            expense_issues.append(
                _issue("MISSING_AMOUNT", "Expense amount is missing or invalid.", "REJECT", index)
            )
        elif amount < 0:
            expense_issues.append(
                _issue("NEGATIVE_AMOUNT", "Expense amount cannot be negative.", "REJECT", index)
            )
        else:
            if amount > policy["per_diem_limit"]:
                expense_issues.append(
                    _issue(
                        "PER_DIEM_LIMIT_EXCEEDED",
                        f"Amount {amount:.2f} exceeds per diem limit {policy['per_diem_limit']:.2f}.",
                        "MANUAL_REVIEW",
                        index,
                    )
                )

            category_limit = policy["category_limits"].get(normalized["category"])
            if category_limit is not None and amount > category_limit:
                expense_issues.append(
                    _issue(
                        "CATEGORY_LIMIT_EXCEEDED",
                        (
                            f"Category '{normalized['category']}' amount {amount:.2f} "
                            f"exceeds limit {category_limit:.2f}."
                        ),
                        "MANUAL_REVIEW",
                        index,
                    )
                )

            if amount > policy["receipt_required_over"] and not normalized["receipt_present"]:
                expense_issues.append(
                    _issue(
                        "RECEIPT_REQUIRED",
                        (
                            f"Receipt is required for expenses over "
                            f"{policy['receipt_required_over']:.2f}."
                        ),
                        "REJECT",
                        index,
                    )
                )

        expense_date = _parse_date(normalized.get("date"))
        if not normalized.get("date"):
            expense_issues.append(
                _issue("MISSING_DATE", "Expense date is missing.", "MANUAL_REVIEW", index)
            )
        elif expense_date is None:
            expense_issues.append(
                _issue("INVALID_DATE", "Expense date must use YYYY-MM-DD format.", "MANUAL_REVIEW", index)
            )
        elif expense_date.weekday() >= 5 and not policy["allow_weekend_expenses"]:
            expense_issues.append(
                _issue(
                    "WEEKEND_RESTRICTION",
                    "Weekend expenses are not allowed for this policy profile.",
                    "MANUAL_REVIEW",
                    index,
                )
            )

        if not normalized.get("vendor"):
            warnings.append(
                _issue("MISSING_VENDOR", "Vendor is missing from extracted expense.", "WARNING", index)
            )

        violations.extend(expense_issues)
        normalized["policy_checks"] = {
            "passed": not any(issue["severity"] in {"REJECT", "MANUAL_REVIEW"} for issue in expense_issues),
            "issues": expense_issues,
        }
        validated_expenses.append(normalized)

    status = _status_from_issues(violations)
    result = {
        "agent": "Agent C - Policy Validation Agent",
        "status": status,
        "policy_profile": policy_profile,
        "policy_summary": {
            "per_diem_limit": policy["per_diem_limit"],
            "receipt_required_over": policy["receipt_required_over"],
            "allow_weekend_expenses": policy["allow_weekend_expenses"],
            "category_limits": policy["category_limits"],
        },
        "total_expenses_checked": len(validated_expenses),
        "violations": violations,
        "warnings": warnings,
        "validated_expenses": validated_expenses,
    }

    os.makedirs(base_path, exist_ok=True)
    with open(os.path.join(base_path, "policy_results.json"), "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4)

    return {"compliance": result}


def _metadata_path(state: dict) -> str:
    run_id = state.get("run_id", "run_001")
    return os.path.join("run_storage", run_id, "metadata")


def _load_packet(packet: Any, base_path: str, filenames: List[str]) -> Dict[str, Any]:
    if isinstance(packet, dict) and packet:
        return packet

    for filename in filenames:
        path = os.path.join(base_path, filename)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                return data

    return {}


def _coerce_expenses(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not extracted:
        return []
    if isinstance(extracted.get("expenses"), list):
        return [expense for expense in extracted["expenses"] if isinstance(expense, dict)]
    if isinstance(extracted.get("items"), list):
        return [expense for expense in extracted["items"] if isinstance(expense, dict)]
    if any(key in extracted for key in ("vendor", "amount", "date", "currency", "category")):
        return [extracted]
    return []


def _normalize_expense(expense: Dict[str, Any], context_receipt_present: bool) -> Dict[str, Any]:
    vendor = str(expense.get("vendor") or "").strip()
    category = str(expense.get("category") or "").strip().lower() or _infer_category(vendor)
    amount = _parse_amount(expense.get("amount"))
    receipt_present = _receipt_present(expense, context_receipt_present)

    return {
        "vendor": vendor,
        "amount": amount,
        "currency": str(expense.get("currency") or "EUR").strip().upper(),
        "date": str(expense.get("date") or "").strip(),
        "category": category,
        "receipt_present": receipt_present,
        "confidence": expense.get("confidence"),
    }


def _infer_category(vendor: str) -> str:
    vendor_lower = vendor.lower()
    for hint, category in VENDOR_CATEGORY_HINTS.items():
        if hint in vendor_lower:
            return category
    return "misc"


def _parse_amount(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _parse_date(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _context_receipt_present(context: Dict[str, Any]) -> bool:
    classification = context.get("document_classification", {})
    return bool(
        classification.get("is_supported")
        and (classification.get("file_name") or classification.get("absolute_file_path"))
    )


def _receipt_present(expense: Dict[str, Any], context_receipt_present: bool) -> bool:
    for key in ("receipt_present", "has_receipt", "receipt_attached"):
        if key in expense:
            return bool(expense[key])
    return bool(
        expense.get("receipt_id")
        or expense.get("source_file")
        or expense.get("file_name")
        or context_receipt_present
    )


def _issue(code: str, message: str, severity: str, expense_index: Optional[int] = None) -> Dict[str, Any]:
    issue = {
        "code": code,
        "severity": severity,
        "message": message,
    }
    if expense_index is not None:
        issue["expense_index"] = expense_index
    return issue


def _status_from_issues(violations: List[Dict[str, Any]]) -> str:
    severities = {issue["severity"] for issue in violations}
    if "REJECT" in severities:
        return "REJECT"
    if "MANUAL_REVIEW" in severities:
        return "MANUAL_REVIEW"
    return "APPROVE"
