import json
import tempfile
import unittest
from pathlib import Path

from backend.agents.agent_c import agent_c_compliance


class AgentCPolicyValidationTests(unittest.TestCase):
    def test_approves_standard_expense_and_writes_policy_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            state = {
                "base_path": str(base_path),
                "context": {
                    "policy_profile": "STANDARD_CORPORATE",
                    "document_classification": {
                        "file_name": "receipt.pdf",
                        "is_supported": True,
                    },
                },
                "extracted": {
                    "vendor": "Restaurant ABC",
                    "amount": 25,
                    "currency": "EUR",
                    "date": "2026-06-16",
                    "category": "meal",
                },
            }

            result = agent_c_compliance(state)["compliance"]

            self.assertEqual("APPROVE", result["status"])
            self.assertEqual(1, result["total_expenses_checked"])
            self.assertEqual([], result["violations"])
            self.assertTrue((base_path / "policy_results.json").exists())
            saved = json.loads((base_path / "policy_results.json").read_text())
            self.assertEqual("APPROVE", saved["status"])

    def test_rejects_missing_receipt_and_flags_weekend_restriction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state = {
                "base_path": temp_dir,
                "context": {"policy_profile": "STANDARD_CORPORATE"},
                "extracted": {
                    "expenses": [
                        {
                            "vendor": "Hotel Central",
                            "amount": 275,
                            "currency": "EUR",
                            "date": "2026-06-20",
                            "category": "lodging",
                            "receipt_present": False,
                        }
                    ]
                },
            }

            result = agent_c_compliance(state)["compliance"]
            codes = {issue["code"] for issue in result["violations"]}

            self.assertEqual("REJECT", result["status"])
            self.assertIn("RECEIPT_REQUIRED", codes)
            self.assertIn("WEEKEND_RESTRICTION", codes)
            self.assertIn("CATEGORY_LIMIT_EXCEEDED", codes)
            self.assertIn("PER_DIEM_LIMIT_EXCEEDED", codes)

    def test_loads_context_and_extracted_packets_from_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            (base_path / "context_packet.json").write_text(
                json.dumps(
                    {
                        "policy_profile": "TECHNICAL_RESEARCH_HIGH_LIMIT",
                        "document_classification": {
                            "file_name": "receipt.pdf",
                            "is_supported": True,
                        },
                    }
                )
            )
            (base_path / "extracted_expenses.json").write_text(
                json.dumps(
                    {
                        "vendor": "Software Subscription",
                        "amount": "750",
                        "currency": "EUR",
                        "date": "2026-06-18",
                        "category": "software",
                    }
                )
            )

            result = agent_c_compliance({"base_path": str(base_path)})["compliance"]

            self.assertEqual("MANUAL_REVIEW", result["status"])
            self.assertEqual("TECHNICAL_RESEARCH_HIGH_LIMIT", result["policy_profile"])
            self.assertEqual(
                {"PER_DIEM_LIMIT_EXCEEDED"},
                {issue["code"] for issue in result["violations"]},
            )


if __name__ == "__main__":
    unittest.main()
